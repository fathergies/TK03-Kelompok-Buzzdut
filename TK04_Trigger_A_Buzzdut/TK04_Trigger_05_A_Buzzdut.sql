SET search_path TO TIKTAKTUK, public;

DROP TRIGGER IF EXISTS trg_prevent_delete_assigned_seat ON TIKTAKTUK.SEAT;
DROP TRIGGER IF EXISTS trg_validate_ticket_category_quota ON TIKTAKTUK.TICKET;
DROP FUNCTION IF EXISTS prevent_delete_assigned_seat();
DROP FUNCTION IF EXISTS validate_ticket_category_quota();

CREATE OR REPLACE FUNCTION prevent_delete_assigned_seat()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM TIKTAKTUK.HAS_RELATIONSHIP hr
        WHERE hr.seat_id = OLD.seat_id
    ) THEN
        RAISE EXCEPTION 'ERROR: Kursi % - Baris % No. % tidak dapat dihapus karena sudah terisi.',
            OLD.section, OLD.row_number, OLD.seat_number;
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_delete_assigned_seat
BEFORE DELETE ON TIKTAKTUK.SEAT
FOR EACH ROW
EXECUTE FUNCTION prevent_delete_assigned_seat();

CREATE OR REPLACE FUNCTION validate_ticket_category_quota()
RETURNS TRIGGER AS $$
DECLARE
    category_name_value TEXT;
    category_quota INTEGER;
    sold_ticket_count INTEGER;
BEGIN
    SELECT tc.category_name, tc.quota
    INTO category_name_value, category_quota
    FROM TIKTAKTUK.TICKET_CATEGORY tc
    WHERE tc.category_id = NEW.tcategory_id;

    SELECT COUNT(*)
    INTO sold_ticket_count
    FROM TIKTAKTUK.TICKET t
    WHERE t.tcategory_id = NEW.tcategory_id;

    IF sold_ticket_count >= category_quota THEN
        RAISE EXCEPTION 'ERROR: Kuota kategori tiket "%" sudah penuh. Tidak dapat membuat tiket baru.',
            category_name_value;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_ticket_category_quota
BEFORE INSERT ON TIKTAKTUK.TICKET
FOR EACH ROW
EXECUTE FUNCTION validate_ticket_category_quota();
