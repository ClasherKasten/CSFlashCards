create table if not exists users(
    id integer primary key autoincrement,
    username text unique,
    password text,
    color_scheme text default "236,235,234",
    light_scheme integer default 0
);
