SET search_path TO TIKTAKTUK, public;

-- Fungsi untuk Validasi Venue (Insert/Update & Delete)
CREATE OR REPLACE FUNCTION validate_venue_operations()
RETURNS TRIGGER AS $$
DECLARE
    existing_venue_id UUID;
    event_count INTEGER;
BEGIN
    -- 1. LOGIKA INSERT ATAU UPDATE (Cek Duplikasi Nama di Kota yang Sama)
    IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') THEN
        SELECT venue_id INTO existing_venue_id 
        FROM TIKTAKTUK.VENUE 
        WHERE LOWER(venue_name) = LOWER(NEW.venue_name) 
          AND LOWER(city) = LOWER(NEW.city)
          AND venue_id != COALESCE(NEW.venue_id, '00000000-0000-0000-0000-000000000000'::UUID);

        IF existing_venue_id IS NOT NULL THEN
            RAISE EXCEPTION 'ERROR: Venue "%" di kota "%" sudah terdaftar dengan ID %.', 
                NEW.venue_name, NEW.city, existing_venue_id;
        END IF;
        RETURN NEW;

    -- 2. LOGIKA DELETE (Cek Event Aktif)
    ELSIF (TG_OP = 'DELETE') THEN
        SELECT COUNT(*) INTO event_count 
        FROM TIKTAKTUK.EVENT 
        WHERE venue_id = OLD.venue_id 
          AND event_datetime >= CURRENT_TIMESTAMP;

        IF event_count > 0 THEN
            RAISE EXCEPTION 'ERROR: Venue "%" masih memiliki event aktif sehingga tidak dapat dihapus.', 
                OLD.venue_name;
        END IF;
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_venue_upsert_check
BEFORE INSERT OR UPDATE ON TIKTAKTUK.VENUE
FOR EACH ROW
EXECUTE FUNCTION validate_venue_operations();

CREATE TRIGGER trg_venue_delete_check
BEFORE DELETE ON TIKTAKTUK.VENUE
FOR EACH ROW
EXECUTE FUNCTION validate_venue_operations();