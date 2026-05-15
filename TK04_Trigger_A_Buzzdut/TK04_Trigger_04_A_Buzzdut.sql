 CREATE OR REPLACE FUNCTION validate_order_promotion()
RETURNS TRIGGER AS $$
DECLARE
    promo_record RECORD;
    usage_count INTEGER;
    event_date DATE;
BEGIN

    SELECT *
    INTO promo_record
    FROM PROMOTION
    WHERE promotion_id = NEW.promotion_id;

    IF promo_record IS NULL THEN
        RAISE EXCEPTION
        'ERROR: Promotion dengan ID % tidak ditemukan.',
        NEW.promotion_id;
    END IF;

    SELECT COUNT(*)
    INTO usage_count
    FROM ORDER_PROMOTION
    WHERE promotion_id = NEW.promotion_id;

    IF usage_count >= promo_record.usage_limit THEN
        RAISE EXCEPTION
        'ERROR: Promotion "%" telah mencapai batas maksimum penggunaan.',
        promo_record.promo_code;
    END IF;

    SELECT DATE(e.event_datetime)
    INTO event_date
    FROM "ORDER" o
    JOIN TICKET t
        ON t.torder_id = o.order_id
    JOIN TICKET_CATEGORY tc
        ON tc.category_id = t.tcategory_id
    JOIN EVENT e
        ON e.event_id = tc.tevent_id
    WHERE o.order_id = NEW.order_id
    LIMIT 1;

    -- validasi tanggal event
    IF event_date < promo_record.start_date
       OR event_date > promo_record.end_date
    THEN
        RAISE EXCEPTION
        'ERROR: Promotion "%" tidak berlaku untuk tanggal event ini.',
        promo_record.promo_code;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;