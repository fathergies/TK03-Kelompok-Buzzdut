SET search_path TO TIKTAKTUK, public;

CREATE OR REPLACE FUNCTION validate_username_putih()
RETURNS TRIGGER AS $$
BEGIN
    -- 1. Mencegah Karakter Spesial (Hanya huruf dan angka) 
    IF NEW.username !~ '^[a-zA-Z0-9]+$' THEN
        RAISE EXCEPTION 'ERROR: Username "%" hanya boleh mengandung huruf dan angka tanpa simbol atau spasi.', NEW.username;
    END IF;

    -- 2. Pengecekan Username Terdaftar (Case-insensitive) 
    IF EXISTS (SELECT 1 FROM TIKTAKTUK.USER_ACCOUNT WHERE LOWER(username) = LOWER(NEW.username)) THEN
        RAISE EXCEPTION 'ERROR: Username "%" sudah terdaftar, gunakan username lain.', NEW.username;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_username_putih
BEFORE INSERT ON TIKTAKTUK.USER_ACCOUNT
FOR EACH ROW
EXECUTE FUNCTION validate_username_putih();