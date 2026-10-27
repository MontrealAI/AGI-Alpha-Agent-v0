-- SPDX-License-Identifier: Apache-2.0
PRAGMA integrity_check;
SELECT count(*) AS preserved_park_rows FROM parks;
SELECT count(*) AS preserved_facility_rows FROM facilities;
SELECT status, count(*) AS n FROM facilities GROUP BY status ORDER BY status;
SELECT count(*) AS unaccounted_rows
FROM facilities f LEFT JOIN exception_queue q ON f.source_row = q.source_row
WHERE f.status != 'confirmed' AND q.source_row IS NULL;
SELECT count(*) AS false_confirmations
FROM facilities
WHERE status = 'confirmed' AND (confirmed_park = '' OR confirmed_park != declared_park);
SELECT borough, count(*) AS rows, sum(status='confirmed') AS confirmed
FROM facilities GROUP BY borough ORDER BY borough;
SELECT id, file, sha256 FROM source_provenance;
