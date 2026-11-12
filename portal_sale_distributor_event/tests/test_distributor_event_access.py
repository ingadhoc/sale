##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestDistributorEventAccess(TransactionCase):
    """In 19.0 the distributor, as a portal user, read only the events published on the
    website (and their tickets) when website_event was installed, and all of them when it
    was not. In 20.0 the rules of website_event are accesses of base.group_everyone and are
    added to the ones of the group, so the access of the module has to carry the filter."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.has_website_event = "website_published" in cls.env["event.event"]._fields
        cls.distributor = cls.env["res.users"].create(
            {
                "name": "Distribuidor event test",
                "login": "distributor_event_access_test",
                "company_id": cls.env.ref("base.main_company").id,
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_portal").id,
                            cls.env.ref("portal_backend.group_portal_backend").id,
                            cls.env.ref("portal_sale_distributor.group_portal_backend_distributor").id,
                        ],
                    )
                ],
            }
        )
        now = fields.Datetime.now()
        vals = {"date_begin": now + timedelta(days=10), "date_end": now + timedelta(days=11)}
        cls.published = cls.env["event.event"].create({"name": "Evento publicado test", **vals})
        cls.unpublished = cls.env["event.event"].create({"name": "Evento sin publicar test", **vals})
        if cls.has_website_event:
            cls.published.website_published = True
            cls.unpublished.website_published = False
        cls.ticket_published = cls.env["event.event.ticket"].create(
            {"name": "Ticket publicado test", "event_id": cls.published.id}
        )
        cls.ticket_unpublished = cls.env["event.event.ticket"].create(
            {"name": "Ticket sin publicar test", "event_id": cls.unpublished.id}
        )

    def _visible(self, records):
        return records.with_user(self.distributor).search([("id", "in", records.ids)])

    def test_published_event_and_ticket_are_visible(self):
        events = self.published + self.unpublished
        tickets = self.ticket_published + self.ticket_unpublished
        with self.subTest("lee el evento publicado y su ticket"):
            self.assertIn(self.published, self._visible(events))
            self.assertIn(self.ticket_published, self._visible(tickets))
            self.assertTrue(self.published.with_user(self.distributor).has_access("read"))
            self.assertTrue(self.ticket_published.with_user(self.distributor).has_access("read"))
        with self.subTest("no escribe ni crea eventos"):
            self.assertFalse(self.published.with_user(self.distributor).has_access("write"))
            self.assertFalse(self.published.with_user(self.distributor).has_access("create"))

    def test_unpublished_event_and_ticket_with_website_event(self):
        if not self.has_website_event:
            self.skipTest("website_event no está instalado")
        with self.subTest("no ve el evento sin publicar"):
            self.assertEqual(self._visible(self.published + self.unpublished), self.published)
            self.assertFalse(self.unpublished.with_user(self.distributor).has_access("read"))
        with self.subTest("no ve el ticket de un evento sin publicar"):
            self.assertEqual(self._visible(self.ticket_published + self.ticket_unpublished), self.ticket_published)
            self.assertFalse(self.ticket_unpublished.with_user(self.distributor).has_access("read"))
        with self.subTest("al despublicar el evento deja de verlo, y vuelve al publicarlo"):
            self.published.website_published = False
            self.assertFalse(self._visible(self.published))
            self.assertFalse(self._visible(self.ticket_published))
            self.published.website_published = True
            self.assertTrue(self._visible(self.published))

    def test_unpublished_event_and_ticket_without_website_event(self):
        if self.has_website_event:
            self.skipTest("website_event está instalado")
        with self.subTest("sin website_event no hay nada que publicar: ve todos"):
            self.assertEqual(self._visible(self.published + self.unpublished), self.published + self.unpublished)
            self.assertEqual(
                self._visible(self.ticket_published + self.ticket_unpublished),
                self.ticket_published + self.ticket_unpublished,
            )
