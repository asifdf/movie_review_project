from flask import Flask, render_template, request, redirect, url_for
import psycopg2

app = Flask(__name__)

print("debug: starting database connection")

# PostgreSQL 연결
conn = psycopg2.connect(
    dbname="term",
    user="postgres",
    password="0000",   # 네 PostgreSQL 비밀번호
    host="localhost",
    port="5432"
)

print("debug: database connection established")


def get_relationship_sets(cur, user_id):
    cur.execute(
        "SELECT opid, tie FROM ties WHERE id = %s",
        (user_id,)
    )
    rows = cur.fetchall()
    following = {opid for opid, tie in rows if tie == 'follow'}
    muted = {opid for opid, tie in rows if tie == 'mute'}
    return following, muted


# -----------------------------
# 로그인 페이지
# -----------------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['id']
        pw = request.form['pw']

        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE id = %s AND password = %s",
            (user_id, pw)
        )

        user = cur.fetchone()
        cur.close()

        if user:
            return redirect(url_for('main', user_id=user_id))
        else:
            return "아이디 또는 비밀번호가 틀렸습니다."

    return render_template('login.html')


# -----------------------------
# 메인 페이지
# -----------------------------
@app.route('/main/<user_id>')
def main(user_id):
    view = request.args.get('view', 'following')
    cur = conn.cursor()

    following, _ = get_relationship_sets(cur, user_id)

    cur.execute("SELECT id FROM users WHERE id <> %s ORDER BY id", (user_id,))
    users = [row[0] for row in cur.fetchall()]

    # 영화 목록
    cur.execute("""
        SELECT id, title, director, genre, rel_date
        FROM movies
        ORDER BY rel_date DESC
    """)
    movies = cur.fetchall()

    # 전체 리뷰 목록
    cur.execute("""
        SELECT reviews.mid, reviews.uid, reviews.ratings, reviews.review, reviews.rev_time, movies.title
        FROM reviews
        JOIN movies ON reviews.mid = movies.id
        ORDER BY reviews.rev_time DESC
    """)
    reviews = cur.fetchall()

    filtered_reviews = []
    for review in reviews:
        reviewer = review[1]
        if view == 'following' and reviewer not in following:
            continue
        filtered_reviews.append(review)

    cur.close()

    return render_template(
        'main.html',
        user_id=user_id,
        movies=movies,
        reviews=filtered_reviews,
        users=users,
        following=following,
        view=view
    )


@app.route('/tie/<action>/<target_id>/<user_id>')
def tie_action(action, target_id, user_id):
    if target_id == user_id:
        return redirect(request.referrer or url_for('main', user_id=user_id))

    if action not in ('follow', 'unfollow'):
        return redirect(request.referrer or url_for('main', user_id=user_id))

    cur = conn.cursor()
    try:
        if action == 'follow':
            cur.execute(
                "INSERT INTO ties (id, opid, tie) VALUES (%s, %s, 'follow') ON CONFLICT DO NOTHING",
                (user_id, target_id)
            )
        elif action == 'unfollow':
            cur.execute(
                "DELETE FROM ties WHERE id = %s AND opid = %s AND tie = 'follow'",
                (user_id, target_id)
            )
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        cur.close()

    return redirect(request.referrer or url_for('main', user_id=user_id))


# -----------------------------
# 영화 상세 / 리뷰 작성 페이지
# -----------------------------
@app.route('/movie/<int:movie_id>/<user_id>', methods=['GET', 'POST'])
def movie_info(movie_id, user_id):
    view = request.args.get('view', 'following')
    message = request.args.get('msg')
    cur = conn.cursor()

    following, _ = get_relationship_sets(cur, user_id)

    # POST 요청은 리뷰 작성/수정, 리뷰 신고, 또는 좌석 예약 중 하나임
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'review':
            rating = request.form['rating']
            review_text = request.form['review']

            try:
                # 기존 리뷰 있는지 확인
                cur.execute(
                    "SELECT * FROM reviews WHERE mid = %s AND uid = %s",
                    (movie_id, user_id)
                )
                existing = cur.fetchone()

                if existing:
                    # 리뷰 수정
                    cur.execute("""
                        UPDATE reviews
                        SET ratings = %s,
                            review = %s,
                            rev_time = NOW()
                        WHERE mid = %s AND uid = %s
                    """, (rating, review_text, movie_id, user_id))
                else:
                    # 새 리뷰 등록
                    cur.execute("""
                        INSERT INTO reviews (mid, uid, ratings, review, rev_time)
                        VALUES (%s, %s, %s, %s, NOW())
                    """, (movie_id, user_id, rating, review_text))

                conn.commit()
                message = '리뷰가 성공적으로 등록/수정되었습니다.'

            except Exception as e:
                conn.rollback()
                cur.close()
                return f"에러 발생: {e}"

        elif action == 'report':
            reviewer_id = request.form['reviewer_id']
            reason = request.form.get('reason', '').strip()
            if reviewer_id == user_id:
                message = '자기 리뷰는 신고할 수 없습니다.'
            elif not reason:
                message = '신고 사유를 입력해주세요.'
            else:
                try:
                    cur.execute("""
                        INSERT INTO reports (review_mid, review_uid, reporter_uid, reason, report_time)
                        VALUES (%s, %s, %s, %s, NOW())
                    """, (movie_id, reviewer_id, user_id, reason))
                    conn.commit()
                    message = '리뷰 신고가 접수되었습니다.'
                except Exception as e:
                    conn.rollback()
                    cur.close()
                    return f"신고 중 오류가 발생했습니다: {e}"

        elif action == 'reserve':
            show_date = request.form['show_date']
            seat_number = request.form['seat_number']

            try:
                # Transaction: 좌석 예약 시 좌석 중복 확인과 삽입은 하나의 트랜잭션 안에서 처리해야 무결성이 보장됨
                conn.autocommit = False
                cur.execute(
                    "SELECT id FROM reservations WHERE movie_id = %s AND seat_number = %s AND reserve_time::date = %s",
                    (movie_id, seat_number, show_date)
                )
                if cur.fetchone():
                    raise ValueError('이미 예약된 좌석입니다. 다른 좌석을 선택하세요.')

                cur.execute(
                    "INSERT INTO reservations (movie_id, user_id, seat_number, reserve_time) VALUES (%s, %s, %s, %s)",
                    (movie_id, user_id, seat_number, show_date)
                )
                conn.commit()
                message = '좌석 예매가 완료되었습니다.'

            except Exception as e:
                conn.rollback()
                cur.close()
                return f"예매 중 오류가 발생했습니다: {e}"

            finally:
                conn.autocommit = True

        else:
            message = '알 수 없는 요청입니다.'

        cur.close()
        return redirect(url_for('movie_info', movie_id=movie_id, user_id=user_id, msg=message))

    # 영화 정보
    cur.execute("""
        SELECT id, title, director, genre, rel_date
        FROM movies
        WHERE id = %s
    """, (movie_id,))
    movie = cur.fetchone()

    # 평균 평점
    cur.execute("""
        SELECT ROUND(AVG(ratings)::numeric, 1)
        FROM reviews
        WHERE mid = %s
    """, (movie_id,))
    avg_rating = cur.fetchone()[0]
    if avg_rating is None:
        avg_rating = '평점 없음'

    # 리뷰 목록
    cur.execute("""
        SELECT uid, ratings, review, rev_time
        FROM reviews
        WHERE mid = %s
        ORDER BY rev_time DESC
    """, (movie_id,))
    reviews = cur.fetchall()

    # 예매된 좌석 목록
    cur.execute("""
        SELECT seat_number, reserve_time, user_id
        FROM reservations
        WHERE movie_id = %s
        ORDER BY reserve_time DESC
    """, (movie_id,))
    reservations = cur.fetchall()

    filtered_reviews = []
    for review in reviews:
        reviewer = review[0]
        if view == 'following' and reviewer not in following:
            continue
        filtered_reviews.append(review)

    cur.close()

    return render_template(
        'movie_info.html',
        movie=movie,
        user_id=user_id,
        avg_rating=avg_rating,
        reviews=filtered_reviews,
        following=following,
        view=view,
        reservations=reservations,
        message=message
    )


# -----------------------------
# 실행
# -----------------------------
if __name__ == '__main__':
    print("Flask 시작 시도")
    app.run(debug=True, port=8000)    