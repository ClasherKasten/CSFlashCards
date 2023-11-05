-- drop table if exists cards;
create table if not exists cards (
  id integer primary key autoincrement,
  type tinyint not null, /* 1 for vocab, 2 for code */
  front text not null,
  back text not null,
  known boolean default 0,
  programming_language text
);

create table if not exists tags (
  id integer primary key autoincrement,
  name text not null,
  -- card_id integer,
  -- foreign key (card_id) references cards(id)
);
