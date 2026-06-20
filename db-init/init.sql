-- Postgres konteyner birinchi marta ko'tarilganda avtomatik ishlaydi (default DB: app).
-- Ikkinchi bazani va biznes bazasi uchun READ-ONLY rolni yaratadi.

CREATE DATABASE demo_biz;

-- Agent shu rol bilan biznes bazasiga ulanadi — faqat o'qiy oladi.
CREATE ROLE readonly_user LOGIN PASSWORD 'readonly_pw';

\connect demo_biz

GRANT CONNECT ON DATABASE demo_biz TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;

-- Hozir mavjud jadvallar (hali yo'q, lekin xavfsizlik uchun):
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- Seed keyinchalik yaratadigan jadvallarga ham avtomatik SELECT bersin (analytics yaratadi):
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

-- readonly_user hech qachon yoza olmasin:
REVOKE CREATE ON SCHEMA public FROM readonly_user;
