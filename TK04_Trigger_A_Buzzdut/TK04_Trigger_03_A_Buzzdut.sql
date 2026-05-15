SET search_path TO TIKTAKTUK, public;

-- ============================================================
-- TK04 Trigger 3 - TikTakTuk
-- Kelompok: Buzzdut
--
-- 1. Validasi artist_id dan event_id pada EVENT_ARTIST
-- 2. Menampilkan sisa kuota Ticket Category berdasarkan event_id
-- ============================================================


-- ============================================================
-- BAGIAN 1
-- Validasi artist_id dan event_id pada EVENT_ARTIST
-- ============================================================

DROP TRIGGER IF EXISTS trg_event_artist_check ON TIKTAKTUK.EVENT_ARTIST;
DROP FUNCTION IF EXISTS TIKTAKTUK.validate_event_artist();

CREATE OR REPLACE FUNCTION TIKTAKTUK.validate_event_artist()
RETURNS TRIGGER AS $$
DECLARE
    v_artist_name TEXT;
    v_event_title TEXT;
BEGIN
    -- Cek apakah artist_id terdaftar
    SELECT a.name
    INTO v_artist_name
    FROM TIKTAKTUK.ARTIST a
    WHERE a.artist_id = NEW.artist_id;

    IF v_artist_name IS NULL THEN
        RAISE EXCEPTION 'ERROR: Artist dengan ID % tidak ditemukan.', NEW.artist_id;
    END IF;

    -- Cek apakah event_id terdaftar
    SELECT e.event_title
    INTO v_event_title
    FROM TIKTAKTUK.EVENT e
    WHERE e.event_id = NEW.event_id;

    IF v_event_title IS NULL THEN
        RAISE EXCEPTION 'ERROR: Event dengan ID % tidak ditemukan.', NEW.event_id;
    END IF;

    -- Cek apakah artist yang sama sudah terdaftar di event yang sama
    IF EXISTS (
        SELECT 1
        FROM TIKTAKTUK.EVENT_ARTIST ea
        WHERE ea.artist_id = NEW.artist_id
          AND ea.event_id = NEW.event_id
    ) THEN
        RAISE EXCEPTION 'ERROR: Artist "%" sudah terdaftar pada event "%".',
            v_artist_name, v_event_title;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_event_artist_check
BEFORE INSERT ON TIKTAKTUK.EVENT_ARTIST
FOR EACH ROW
EXECUTE FUNCTION TIKTAKTUK.validate_event_artist();



-- ============================================================
-- BAGIAN 2
-- Menampilkan Sisa Kuota Ticket Category Berdasarkan event_id
-- ============================================================

DROP FUNCTION IF EXISTS TIKTAKTUK.get_ticket_category_remaining_quota(UUID);

CREATE OR REPLACE FUNCTION TIKTAKTUK.get_ticket_category_remaining_quota(p_event_id UUID)
RETURNS TABLE (
    category_id UUID,
    category_name VARCHAR,
    quota INTEGER,
    sold_ticket BIGINT,
    remaining_quota INTEGER
) AS $$
BEGIN
    -- Cek apakah event_id terdaftar
    IF NOT EXISTS (
        SELECT 1
        FROM TIKTAKTUK.EVENT e
        WHERE e.event_id = p_event_id
    ) THEN
        RAISE EXCEPTION 'ERROR: Event dengan ID % tidak ditemukan.', p_event_id;
    END IF;

    -- Menampilkan seluruh Ticket Category milik Event tersebut
    -- beserta sisa kuota = quota awal - jumlah tiket yang sudah dibuat/terjual
    RETURN QUERY
    SELECT
        tc.category_id,
        tc.category_name,
        tc.quota,
        COUNT(t.ticket_id) AS sold_ticket,
        (tc.quota - COUNT(t.ticket_id))::INTEGER AS remaining_quota
    FROM TIKTAKTUK.TICKET_CATEGORY tc
    LEFT JOIN TIKTAKTUK.TICKET t
        ON t.tcategory_id = tc.category_id
    WHERE tc.tevent_id = p_event_id
    GROUP BY tc.category_id, tc.category_name, tc.quota
    ORDER BY tc.category_name;
END;
$$ LANGUAGE plpgsql;