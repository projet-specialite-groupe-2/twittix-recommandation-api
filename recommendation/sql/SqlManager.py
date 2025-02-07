import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool

HOST = "localhost"
PORT = "5432"
USER = "admin"
PASSWORD = "admin"
DB_EXISTING = "lebigprojet"
DB_TARGET = "twittix"

pool = SimpleConnectionPool(minconn=1, maxconn=5,
                            user=USER,
                            password=PASSWORD,
                            host=HOST,
                            port=PORT,
                            database=DB_TARGET)


def get_db_connection():
    """
    Returns a connection from the connection pool.
    :return:  A psycopg2 connection object.
    """
    return pool.getconn()


def release_db_connection(conn):
    """
    Releases a connection back to the connection pool.
    :param conn: psycopg2 connection object.
    """
    pool.putconn(conn)


def get_follows(user_id):
    """
    Returns a list of user IDs that the specified user follows.

    :param user_id: ID of the user for whom we want to retrieve follows.
    :return: A list of integers representing the IDs of followed users.
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT followed_user_id
                FROM follows
                WHERE following_user_id = %s
                """,
                (user_id,)
            )
            rows = cur.fetchall()
    finally:
        release_db_connection(connection)

    return [row[0] for row in rows]


def get_friends(user_id):
    """
    Returns a list of user IDs that have a mutual follow relationship with the specified user.
    In other words, 'user_id' follows X and X also follows 'user_id'.

    :param user_id: ID of the user for whom we want to identify mutual friends.
    :return: A list of integers representing the IDs of users with mutual follow.
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT f1.followed_user_id
                FROM follows f1
                JOIN follows f2
                  ON f1.followed_user_id = f2.following_user_id
                 AND f1.following_user_id = f2.followed_user_id
                WHERE f1.following_user_id = %s
                """,
                (user_id,)
            )
            rows = cur.fetchall()
    finally:
        release_db_connection(connection)

    return [row[0] for row in rows]


def get_unseen_24h_posts_id_from_author_ids(user_id, author_ids):
    """
    Retrieves IDs of the most recent posts (less than 24 hours old) from the given author IDs,
    excluding any posts the specified user has already viewed.

    :param user_id: ID of the user for whom we want to filter out viewed posts.
    :param author_ids: List of user IDs whose posts we want to fetch.
    :return: A list of (post_id,) tuples for unseen posts.
    """
    if not author_ids:
        return []

    connection = get_db_connection()
    try:
        with connection.cursor() as cur:
            placeholders = ','.join(['%s'] * len(author_ids))
            query = f"""
                SELECT p.id
                FROM posts p
                WHERE p.user_id IN ({placeholders})
                  AND p.created_at > (NOW() - INTERVAL '24 HOURS')
                  AND p.id NOT IN (
                    SELECT post
                    FROM post_view_status
                    WHERE "user" = %s
                  )
                ORDER BY p.created_at DESC
            """
            cur.execute(query, author_ids + [user_id])
            rows = cur.fetchall()
    finally:
        release_db_connection(connection)

    return rows


def get_unseen_top_posts_id_last_hour(user_id, limit=10):
    """
    Selects the IDs of posts created within the last hour, ordered by the total number of likes,
    excluding those the specified user has already viewed.

    :param user_id: ID of the user for whom we want to filter out viewed posts.
    :param limit: Maximum number of post IDs to return.
    :return: A list of (post_id, nb_likes) tuples for unseen posts.
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cur:
            query = """
                SELECT p.id, COUNT(l.liked_post_id) AS nb_likes
                FROM posts p
                LEFT JOIN likes l ON p.id = l.liked_post_id
                WHERE p.created_at > (NOW() - INTERVAL '1 HOUR')
                  AND p.id NOT IN (
                    SELECT post
                    FROM post_view_status
                    WHERE "user" = %s
                  )
                GROUP BY p.id
                ORDER BY nb_likes DESC
                LIMIT %s
            """
            cur.execute(query, (user_id, limit))
            rows = cur.fetchall()
    finally:
        release_db_connection(connection)

    return rows


def get_unseen_top_posts_id_last_day_without_last_hour(user_id, limit=10):
    """
    Retrieves the IDs of the most popular posts (based on likes) published between 1 and 24 hours ago,
    excluding posts the specified user has already viewed.

    :param user_id: ID of the user for whom we want to filter out viewed posts.
    :param limit: Maximum number of post IDs to return.
    :return: A list of (post_id, nb_likes) tuples for unseen posts.
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cur:
            query = """
                SELECT p.id, COUNT(l.liked_post_id) AS nb_likes
                FROM posts p
                LEFT JOIN likes l ON p.id = l.liked_post_id
                WHERE p.created_at > (NOW() - INTERVAL '24 HOURS')
                  AND p.created_at < (NOW() - INTERVAL '1 HOUR')
                  AND p.id NOT IN (
                    SELECT post
                    FROM post_view_status
                    WHERE "user" = %s
                  )
                GROUP BY p.id
                ORDER BY nb_likes DESC
                LIMIT %s
            """
            cur.execute(query, (user_id, limit))
            rows = cur.fetchall()
    finally:
        release_db_connection(connection)

    return rows


def get_unseen_newest_posts_id(user_id, limit=100):
    """
    Selects the IDs of the most recently created posts, with no time restriction,
    excluding posts the specified user has already viewed.

    :param user_id: ID of the user for whom we want to filter out viewed posts.
    :param limit: Maximum number of post IDs to return.
    :return: A list of (post_id,) tuples for unseen posts.
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cur:
            query = """
                SELECT p.id
                FROM posts p
                WHERE p.id NOT IN (
                    SELECT post
                    FROM post_view_status
                    WHERE "user" = %s
                )
                ORDER BY p.created_at DESC
                LIMIT %s
            """
            cur.execute(query, (user_id, limit))
            rows = cur.fetchall()
    finally:
        release_db_connection(connection)

    return rows


def get_posts_by_id_list(list_post_id):
    """
    Retrieves all columns of the posts with the specified IDs, returning each row as a dict.
    """
    if not list_post_id:
        return []

    connection = get_db_connection()
    try:
        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            placeholders = ','.join(['%s'] * len(list_post_id))
            query = f"""
                SELECT *
                FROM posts
                WHERE id IN ({placeholders})
            """
            cur.execute(query, list_post_id)
            rows = cur.fetchall()
    finally:
        release_db_connection(connection)

    return [dict(row) for row in rows]


def mark_posts_as_viewed(user_id, post_ids):
    """
    Inserts records into post_view_status for each post in 'post_ids',
    marking them as viewed at the current time by the specified user.

    :param user_id: ID of the user who viewed the posts.
    :param post_ids: List of post IDs to mark as viewed.
    """
    if not post_ids:
        return

    connection = get_db_connection()
    try:
        with connection.cursor() as cur:
            for post_id in post_ids:
                cur.execute(
                    """
                    INSERT INTO post_view_status ("user", "post", "readt_at")
                    VALUES (%s, %s, NOW())
                    """,
                    (user_id, post_id)
                )
        connection.commit()
    finally:
        release_db_connection(connection)
