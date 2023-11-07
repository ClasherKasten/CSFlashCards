create table if not exists users(
    id integer primary key autoincrement,
    username text,
    password text,
    color_scheme text,
    light_scheme integer
);
