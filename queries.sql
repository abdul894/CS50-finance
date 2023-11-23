-- ALTER TABLE buyers
-- ADD COLUMN stock_symbol text;

-- ALTER TABLE buyers
-- ADD COLUMN price INTEGER NOT NULL;

CREATE TABLE buyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER,
    stock_symbol text,
    price FLOAT NOT NULL,
    no_of_stocks INTEGER NOT NULL,
    amount FLOAT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

