-- Doka Cloud Edition — authorization integrity guards.
-- Apply explicitly after reviewing a backup; provisioning D1 does not apply migrations.
--
-- Rules:
-- 1. An organization-owned document must be owned by an organization member.
-- 2. Organization document permissions may only be granted to organization members.
-- 3. A permission grant must be made by the document owner or an org owner/admin.
-- 4. Personal documents may only have permission grants made by their owner.
-- 5. An organization can have at most one owner role.

CREATE UNIQUE INDEX organization_one_owner_idx
    ON organization_members(organization_id)
    WHERE role = 'owner';

CREATE TRIGGER documents_owner_must_be_org_member_insert
BEFORE INSERT ON documents
WHEN NEW.organization_id IS NOT NULL
 AND NOT EXISTS (
    SELECT 1
    FROM organization_members
    WHERE organization_id = NEW.organization_id
      AND user_id = NEW.owner_id
 )
BEGIN
    SELECT RAISE(ABORT, 'document owner must be an organization member');
END;

CREATE TRIGGER documents_owner_must_be_org_member_update
BEFORE UPDATE OF organization_id, owner_id ON documents
WHEN NEW.organization_id IS NOT NULL
 AND NOT EXISTS (
    SELECT 1
    FROM organization_members
    WHERE organization_id = NEW.organization_id
      AND user_id = NEW.owner_id
 )
BEGIN
    SELECT RAISE(ABORT, 'document owner must be an organization member');
END;

CREATE TRIGGER document_permissions_scope_insert
BEFORE INSERT ON document_permissions
WHEN EXISTS (
    SELECT 1
    FROM documents d
    WHERE d.id = NEW.document_id
      AND d.organization_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM organization_members m
          WHERE m.organization_id = d.organization_id
            AND m.user_id = NEW.user_id
      )
)
BEGIN
    SELECT RAISE(ABORT, 'permission recipient must be an organization member');
END;

CREATE TRIGGER document_permissions_granter_insert
BEFORE INSERT ON document_permissions
WHEN NOT EXISTS (
    SELECT 1
    FROM documents d
    WHERE d.id = NEW.document_id
      AND (
          d.owner_id = NEW.granted_by
          OR (
              d.organization_id IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM organization_members m
                  WHERE m.organization_id = d.organization_id
                    AND m.user_id = NEW.granted_by
                    AND m.role IN ('owner', 'admin')
              )
          )
      )
)
BEGIN
    SELECT RAISE(ABORT, 'permission grant requires document owner or organization admin');
END;

CREATE TRIGGER document_permissions_scope_update
BEFORE UPDATE OF document_id, user_id, granted_by ON document_permissions
WHEN EXISTS (
    SELECT 1
    FROM documents d
    WHERE d.id = NEW.document_id
      AND d.organization_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM organization_members m
          WHERE m.organization_id = d.organization_id
            AND m.user_id = NEW.user_id
      )
)
BEGIN
    SELECT RAISE(ABORT, 'permission recipient must be an organization member');
END;

CREATE TRIGGER document_permissions_granter_update
BEFORE UPDATE OF document_id, user_id, granted_by ON document_permissions
WHEN NOT EXISTS (
    SELECT 1
    FROM documents d
    WHERE d.id = NEW.document_id
      AND (
          d.owner_id = NEW.granted_by
          OR (
              d.organization_id IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM organization_members m
                  WHERE m.organization_id = d.organization_id
                    AND m.user_id = NEW.granted_by
                    AND m.role IN ('owner', 'admin')
              )
          )
      )
)
BEGIN
    SELECT RAISE(ABORT, 'permission grant requires document owner or organization admin');
END;
