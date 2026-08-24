import ast
import logging

from odoo.fields import Domain

_logger = logging.getLogger(__name__)

# Arity of the domain prefix operators, used to walk a domain without evaluating it.
OPERATORS = {"!": 1, "&": 2, "|": 2}


def _negate_literal(raw):
    """Negate a domain whose every element is a literal.

    Returns the negated domain as a string, or None if `raw` is not a plain
    literal domain (it may contain dynamic expressions, see `_negate_source`).
    """
    parsed = ast.literal_eval(raw)
    if not isinstance(parsed, (list, tuple)) or not parsed:
        return None
    # Domain normalizes the implicit AND and applies De Morgan, so the stored
    # value stays readable in the `domain` widget.
    return str(~Domain(list(parsed)))


def _negate_source(raw):
    """Negate a domain textually, keeping every element's source verbatim.

    Used when the domain holds dynamic expressions (the field is rendered with
    ``allow_expressions: True``, so it may contain ``context_today()`` or
    ``relativedelta(...)``). Those must NOT be evaluated here: doing so would
    freeze them into the migration date. Returns a string or None if the domain
    cannot be parsed as a well formed prefix domain.
    """
    try:
        node = ast.parse(raw.strip(), mode="eval").body
    except SyntaxError:
        return None
    if not isinstance(node, (ast.List, ast.Tuple)) or not node.elts:
        return None

    # Walk the prefix notation to count how many top level expressions are
    # joined by the implicit AND: normalize(d) == ['&'] * (k - 1) + d
    extra_ands = 0
    expected = 1
    for elt in node.elts:
        if expected == 0:
            extra_ands += 1
            expected = 1
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            if elt.value not in OPERATORS:
                return None
            expected += OPERATORS[elt.value] - 1
        else:
            expected -= 1
    if expected != 0:
        return None

    segments = [ast.get_source_segment(raw, elt) for elt in node.elts]
    if any(segment is None for segment in segments):
        return None

    # A single fully negated domain: negating it again just removes the '!'.
    if not extra_ands and isinstance(node.elts[0], ast.Constant) and node.elts[0].value == "!":
        return "[%s]" % ", ".join(segments[1:])
    return "[%s]" % ", ".join(["'!'"] + ["'&'"] * extra_ands + segments)


def migrate(cr, version):
    """Invert `sale_order_type.invoice_validate_domain` to keep v18 behaviour.

    The meaning of the field was flipped when invoice exclusion was introduced:

    * before: ``invoices.filtered_domain(domain)`` -> invoices matching the
      domain were the ones being validated;
    * now: ``invoices - invoices.filtered_domain(domain)`` -> invoices matching
      the domain are the ones left in draft.

    So every stored domain has to be negated, otherwise invoices get validated
    exactly the other way around, silently. An empty domain is left untouched:
    it means "validate everything" in both versions, and negating it would
    yield a domain matching nothing.

    This runs on the version that introduced the change instead of 19.0.0.0 so
    that databases already sitting on 19.0.2.0.0 are covered too. Should the
    change ever be backported to 18.0, this script must be revisited: it would
    otherwise invert domains that are already expressed the new way.
    """
    cr.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'sale_order_type'
          AND column_name = 'invoice_validate_domain'
          AND table_schema = current_schema()
        """
    )
    if not cr.fetchone():
        return

    cr.execute(
        """
        SELECT id, invoice_validate_domain
        FROM sale_order_type
        WHERE invoice_validate_domain IS NOT NULL
          AND btrim(invoice_validate_domain) NOT IN ('', '[]')
        ORDER BY id
        """
    )

    for type_id, raw in cr.fetchall():
        try:
            negated = _negate_literal(raw)
        except (ValueError, SyntaxError, TypeError):
            # Not a plain literal: it carries dynamic expressions.
            negated = _negate_source(raw)
        except Exception:
            negated = None

        if not negated:
            _logger.warning(
                "sale.order.type %s: could not invert invoice_validate_domain %r. "
                "It still uses the old meaning and has to be reviewed by hand.",
                type_id,
                raw,
            )
            continue

        cr.execute(
            "UPDATE sale_order_type SET invoice_validate_domain = %s WHERE id = %s",
            (negated, type_id),
        )
        _logger.info("sale.order.type %s: invoice_validate_domain %r -> %r", type_id, raw, negated)
