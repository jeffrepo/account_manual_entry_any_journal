from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestManualEntryJournal(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()
        cls.journals = {
            journal_type: cls.company_data[key]
            for journal_type, key in (
                ("general", "default_journal_misc"),
                ("sale", "default_journal_sale"),
                ("purchase", "default_journal_purchase"),
                ("bank", "default_journal_bank"),
                ("cash", "default_journal_cash"),
                ("credit", "default_journal_credit"),
            )
        }

    def _entry_values(self, journal):
        return {
            "move_type": "entry",
            "company_id": self.company_data["company"].id,
            "journal_id": journal.id,
            "date": fields.Date.today(),
            "line_ids": [
                Command.create({
                    "name": "Manual debit",
                    "account_id": self.company_data["default_account_expense"].id,
                    "debit": 100.0,
                    "tax_ids": [Command.clear()],
                }),
                Command.create({
                    "name": "Manual credit",
                    "account_id": self.company_data["default_account_revenue"].id,
                    "credit": 100.0,
                    "tax_ids": [Command.clear()],
                }),
            ],
        }

    def test_selectable_journals_respect_company_and_archiving(self):
        archived = self.journals["general"].copy({"code": "MARC", "active": False})
        company = self.company_data["company"]
        other_company = self.company_data_2["company"]
        move = self.env["account.move"].with_context(
            allowed_company_ids=[company.id, other_company.id],
        ).new({"move_type": "entry", "company_id": company.id})
        for journal in self.journals.values():
            self.assertIn(journal, move.suitable_journal_ids)
        self.assertNotIn(archived, move.suitable_journal_ids)
        self.assertNotIn(
            self.company_data_2["default_journal_misc"], move.suitable_journal_ids,
        )

    def test_create_recompute_and_post_in_each_journal_type(self):
        for journal_type, journal in self.journals.items():
            with self.subTest(journal_type=journal_type):
                move = self.env["account.move"].create(self._entry_values(journal))
                move._compute_journal_id()
                self.assertEqual(move.journal_id, journal)
                move.action_post()
                self.assertEqual(move.state, "posted")
                self.assertEqual(move.move_type, "entry")
                self.assertEqual(move.journal_id, journal)
                self.assertTrue(move.name)
                self.assertNotEqual(move.name, "/")

    def test_form_keeps_selected_journal_on_save(self):
        for journal_type, journal in self.journals.items():
            with self.subTest(journal_type=journal_type):
                with Form(self.env["account.move"].with_context(default_move_type="entry")) as form:
                    form.journal_id = journal
                    with form.line_ids.new() as line:
                        line.name = "Manual debit"
                        line.account_id = self.company_data["default_account_expense"]
                        line.debit = 100.0
                        line.tax_ids.clear()
                    with form.line_ids.new() as line:
                        line.name = "Manual credit"
                        line.account_id = self.company_data["default_account_revenue"]
                        line.credit = 100.0
                        line.tax_ids.clear()
                self.assertEqual(form.record.journal_id, journal)

    def test_default_journal_remains_miscellaneous(self):
        self.journals["sale"].sequence = -999
        move = self.env["account.move"].new({"move_type": "entry"})
        self.assertEqual(move.journal_id.type, "general")

    def test_invoices_refunds_and_receipts_keep_their_journal_types(self):
        moves = self.env["account.move"]
        for move_type, journal_type in (
            ("entry", "general"),
            ("out_invoice", "sale"),
            ("out_refund", "sale"),
            ("out_receipt", "sale"),
            ("in_invoice", "purchase"),
            ("in_refund", "purchase"),
            ("in_receipt", "purchase"),
        ):
            moves |= self.env["account.move"].create({
                "move_type": move_type,
                "journal_id": self.journals[journal_type].id,
            })
        moves._compute_suitable_journal_ids()
        for move in moves:
            if move.move_type == "entry":
                self.assertIn(self.journals["bank"], move.suitable_journal_ids)
            else:
                self.assertEqual(
                    set(move.suitable_journal_ids.mapped("type")),
                    {move.journal_id.type},
                )
                with self.assertRaises(ValidationError), self.cr.savepoint():
                    move.journal_id = self.journals["general"]

    def test_payment_and_statement_contexts_keep_native_types(self):
        for context_key in ("is_payment", "is_statement_line"):
            with self.subTest(context_key=context_key):
                move = self.env["account.move"].with_context(**{context_key: True}).new({
                    "move_type": "entry",
                })
                self.assertFalse(move._allow_any_journal_for_entry())
                self.assertEqual(set(move._get_valid_journal_types()), {"bank", "cash", "credit"})
                self.assertIn(move.journal_id.type, {"bank", "cash", "credit"})
                self.assertNotIn(self.journals["sale"], move.suitable_journal_ids)

    def test_linked_payment_and_statement_keep_native_types(self):
        payment = self.env["account.payment"].create({
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": self.partner_a.id,
            "journal_id": self.journals["bank"].id,
            "amount": 100.0,
        })
        statement_line = self.env["account.bank.statement.line"].create({
            "journal_id": self.journals["bank"].id,
            "payment_ref": "Journal module test",
            "amount": 100.0,
            "date": fields.Date.today(),
        })
        for field_name, record in (
            ("origin_payment_id", payment),
            ("statement_line_id", statement_line),
        ):
            with self.subTest(field_name=field_name):
                move = self.env["account.move"].new({
                    "move_type": "entry",
                    "journal_id": self.journals["bank"].id,
                    field_name: record.id,
                })
                self.assertFalse(move._allow_any_journal_for_entry())
                self.assertEqual(set(move._get_valid_journal_types()), {"bank", "cash", "credit"})

    def test_unbalanced_entry_is_still_rejected(self):
        values = self._entry_values(self.journals["bank"])
        values["line_ids"] = values["line_ids"][:1]
        with self.assertRaises(UserError), self.cr.savepoint():
            move = self.env["account.move"].with_context(check_move_validity=True).create(values)
            move.action_post()
