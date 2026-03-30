# Migration Order

Apply migrations in lexical order:

1. `01_extensions_and_types.sql`
2. `02_identity_compat.sql`
3. `03_create_tables.sql`
4. `04_normalize_columns.sql`
5. `05_constraints_indexes_triggers.sql`

Rules:

- Use fixed numeric order prefixes.
- Do not use timestamp prefixes in file names.
- Do not include product-version tags such as `v1` or `v2` in file names.
- Keep one migration focused on one responsibility whenever possible.
