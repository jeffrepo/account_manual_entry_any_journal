from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _allow_any_journal_for_entry(self):
        self.ensure_one()
        return (
            self.move_type == "entry"
            and not self.origin_payment_id
            and not self.statement_line_id
            and not self.env.context.get("is_payment")
            and not self.env.context.get("is_statement_line")
        )

    def _get_valid_journal_types(self):
        journal_types = super()._get_valid_journal_types()
        if (
            self._allow_any_journal_for_entry()
            and not self.env.context.get("manual_entry_standard_default_journal")
        ):
            # Include types added by other installed modules as well.
            return self.env["account.journal"]._fields["type"].get_values(self.env)
        return journal_types

    def _search_default_journal(self):
        if self._allow_any_journal_for_entry():
            # Keep Odoo's default journal and currency selection. Expanding the
            # selectable types must not make Sales the default for a new entry.
            default_move = self.with_context(manual_entry_standard_default_journal=True)
            return super(AccountMove, default_move)._search_default_journal()
        return super()._search_default_journal()

    @api.depends(
        "company_id",
        "invoice_filter_type_domain",
        "move_type",
        "origin_payment_id",
        "statement_line_id",
    )
    @api.depends_context("is_payment", "is_statement_line")
    def _compute_suitable_journal_ids(self):
        super()._compute_suitable_journal_ids()
        journal_model = self.env["account.journal"]
        for move in self:
            if move._allow_any_journal_for_entry():
                # Keep native company/branch rules, access rules and the
                # normal active-record filter; do not use sudo().
                move.suitable_journal_ids = journal_model.search(
                    journal_model._check_company_domain(move.company_id or self.env.company)
                )
