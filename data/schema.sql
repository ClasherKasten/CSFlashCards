-- drop table if exists cards;
create table if not exists cards (
  id integer primary key autoincrement,
  type tinyint not null, /* 1 for vocab, 2 for code */
  front text not null,
  back text not null,
  known boolean default 0,
  programming_language text,
  tag_id integer not null,
  foreign key(tag_id) references tags(id)
);

create table if not exists tags (
  id integer primary key autoincrement,
  name text not null
);
