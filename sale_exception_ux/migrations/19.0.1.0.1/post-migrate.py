# Copyright 2024 Adhoc SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
import re

_logger = logging.getLogger(__name__)

# Rewrites exception.rule.code that still references fields removed in v19:
#   sale_warn (res.partner)      -> sale_warn_msg
#   sale_line_warn (product.*)   -> sale_line_warn_msg
#
# Needed for databases migrated from v18: sale_exception ships these rules
# inside <odoo noupdate="1">, so Odoo never rewrites them on upgrade.
_PATTERN = re.compile(
    r"""(?P<obj>\w+(?:\.\w+)*)\.(?P<field>sale_warn|sale_line_warn)\s*"""
    r"""(?:==\s*['"](?:warning|block)['"]|in\s*\([^)]*\))""",
)


def _rewrite(match):
    return "bool(%s.%s_msg)" % (match.group("obj"), match.group("field"))


def migrate(cr, version):
    cr.execute(
        """
        SELECT id, code FROM exception_rule
        WHERE code ~ '(^|[^_])sale_(line_)?warn([^_a-zA-Z]|$)'
        """
    )
    for rule_id, code in cr.fetchall():
        if not code:
            continue
        new_code, n = _PATTERN.subn(_rewrite, code)
        if n and new_code != code:
            cr.execute(
                "UPDATE exception_rule SET code = %s WHERE id = %s",
                (new_code, rule_id),
            )
            _logger.info("sale_exception_ux: exception.rule %s migrated to *_warn_msg", rule_id)
        elif "_msg" not in code:
            _logger.warning(
                "sale_exception_ux: exception.rule %s references sale[_line]_warn "
                "but did not match known pattern; review manually: %s",
                rule_id,
                code,
            )
