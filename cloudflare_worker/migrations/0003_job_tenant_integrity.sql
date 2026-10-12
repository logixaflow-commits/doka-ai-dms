-- Durable jobs are tenant-owned work. The application must derive this value
-- from verified authorization context; a nullable FK is not sufficient.
CREATE TRIGGER jobs_require_organization_insert
BEFORE INSERT ON jobs
WHEN NEW.organization_id IS NULL OR length(trim(NEW.organization_id)) = 0
BEGIN
    SELECT RAISE(ABORT, 'durable jobs require an organization');
END;

CREATE TRIGGER jobs_require_organization_update
BEFORE UPDATE OF organization_id ON jobs
WHEN NEW.organization_id IS NULL OR length(trim(NEW.organization_id)) = 0
BEGIN
    SELECT RAISE(ABORT, 'durable jobs require an organization');
END;
