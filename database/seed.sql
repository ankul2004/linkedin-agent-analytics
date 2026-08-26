-- LinkedIn Agent Analytics - Seed Data

INSERT OR IGNORE INTO dim_status (status_name) VALUES
('NEW'),
('CONTACTED'),
('FOLLOW_UP'),
('INTERVIEW'),
('HIRED'),
('REJECTED');

INSERT OR IGNORE INTO dim_company (company_name) VALUES
('OpenAI'),
('Google'),
('Microsoft'),
('Amazon'),
('Meta');

INSERT OR IGNORE INTO dim_location (location_name) VALUES
('Noida'),
('Delhi'),
('Gurugram'),
('Bengaluru'),
('Hyderabad');

INSERT OR IGNORE INTO dim_date
(date_key, calendar_date, year, quarter, month, month_name, day)
VALUES
(20260820, '2026-08-20', 2026, 3, 8, 'August', 20),
(20260821, '2026-08-21', 2026, 3, 8, 'August', 21),
(20260822, '2026-08-22', 2026, 3, 8, 'August', 22),
(20260823, '2026-08-23', 2026, 3, 8, 'August', 23),
(20260824, '2026-08-24', 2026, 3, 8, 'August', 24);