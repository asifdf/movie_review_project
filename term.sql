DROP TABLE IF EXISTS ties;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS movies;
DROP TABLE IF EXISTS user_info;
DROP TABLE IF EXISTS users;
DROP DOMAIN IF EXISTS domain_email;

create table users(
  id varchar(15) not null primary key,
  password varchar(20) not null,
  role varchar(10) not null check (role in ('admin', 'user')));
  
create DOMAIN domain_email AS text
	CHECK (VALUE~'^\w+@[a-zA-Z_]+?[\.[a-zA-Z]+$');

create table user_info(
  id varchar(15) not null primary key,
  name varchar(15),
  email domain_email,
  reg_date date not null,
  foreign key(id) references users(id));

create table movies(
  id serial primary key,
  title varchar(30) not null,
  director varchar(30) not null,
  genre varchar(20) not null check (genre in ('action', 'comedy', 'drama', 'fantasy', 'horror', 'mystery', 'romance', 'thriller', 'western')),
  rel_date date not null
);

create table reviews(
  mid int not null,
  uid varchar(15) not null,
  ratings smallint not null check (ratings between 0 and 5),
  review text not null,
  rev_time timestamp not null,
  primary key(mid, uid),
  foreign key(mid) references movies(id),
  foreign key(uid) references users(id));

create table ties(
  id varchar(15) not null,
  opid varchar(15) not null,
  tie varchar(8) not null check (tie in ('follow', 'mute')),
  primary key(id, opid),
  foreign key(id) references users(id),
  foreign key(opid) references users(id));
  
create table reports(
  id serial primary key,
  review_mid int,
  review_uid varchar(20),
  reporter_uid varchar(20),
  reason text,
  report_time timestamp default now(),
  foreign key (review_mid) references movies(id),
  foreign key (review_uid) references users(id),
  foreign key (reporter_uid) references users(id)
);

create table reservations(
  id serial primary key,
  movie_id int references movies(id),
  user_id varchar(20) references users(id),
  seat_number varchar(10),
  reserve_time timestamp default now()
);
  
insert into users values('admin', '0000', 'admin');
insert into users values('admin2', '0000', 'admin');
insert into users values('andy', '0000', 'user');
insert into users values('lisa', '1234', 'user');
 
insert into user_info values('admin', 'admin', 'admin@korea.ac.kr', now());
insert into user_info values('admin2', 'admin2', 'admin2@korea.ac.kr', now());
insert into user_info values('andy', null, null, now());
insert into user_info values('lisa', null, null, now());

insert into ties values ('andy', 'lisa', 'follow');
insert into ties values ('lisa', 'andy', 'follow');

insert into movies(title, director, genre, rel_date) values
  ('The Shawshank Redemption', 'Frank Darabont', 'drama', '1995-01-28'),
  ('12 Angry Men', 'Sidney Lumet', 'drama', '1957-04-01'),
  ('Star Wars', 'George Lucas', 'fantasy', '1977-05-25'),
  ('Toy Story', 'John Lasseter', 'comedy', '1995-12-23'),
  ('The Truman Show', 'Peter Weir', 'comedy', '1998-10-24'),
  ('Nuovo Cinema Paradiso', 'Giuseppe Tornatore', 'drama', '1988-09-29');
  
insert into reviews values
  (1, 'admin', 4, 'An incredible movie. One that lives with you.', now()-interval'30day 1 hour 2 minute'),
  (1, 'andy', 5, 'the best movie in history and the best ending in any entertainment business', now()-interval'3 month 5 hour'),
  (2, 'admin', 5, 'What a Character-Study is Meant to Be.', now()-interval'34 day 34 hour'),
  (2, 'andy', 4, 'So Simple, So Brilliant', now()-interval'190hour 1 minute'),
  (3, 'admin', 5, 'In A Galaxy Far Away................A Franchise Was Born', now()-interval'3943hour 4 minute'),
  (3, 'andy', 5, 'The Force will be with you, always.', now()-interval'31 minute'),
  (4, 'admin', 4, 'Plastic Fantastic.', now()-interval'10 minute'),
  (4, 'andy', 5, 'It really is that good. It''s taken me 27 years to realise.', now()-interval'13 minute'),
  (5, 'admin', 5, 'Good Afternoon, Good Evening, and Goodnight.', now()-interval'30 hour'),
  (5, 'andy', 4, 'Incredibly surreal', now()),
  (5, 'lisa', 4, 'The film is an amazing combination of existentialism, surrealism, and symbolism.', now());
  