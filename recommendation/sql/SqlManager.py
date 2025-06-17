import os
from typing import Optional

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool

HOST = os.getenv("DB_HOST", "localhost")
PORT = os.getenv("DB_PORT", "5432")
USER = os.getenv("DB_USER", "admin")
PASSWORD = os.getenv("DB_PASSWORD", "admin")
DB_EXISTING = os.getenv("DB_EXISTING", "lebigprojet")
DB_TARGET = os.getenv("DB_TARGET", "twittix")


class DBConnectionManager:
    def __init__(self):
        self.pool = SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            database=DB_TARGET
        )

    def get_conn(self):
        return self.pool.getconn()

    def release_conn(self, conn):
        self.pool.putconn(conn)


db_manager: Optional[DBConnectionManager] = None


def init_db_manager():
    """
    Initializes the global DB connection manager.
    """

    global db_manager
    if db_manager is None:
        db_manager = DBConnectionManager()


def get_db_connection():
    """
    Returns a connection from the connection pool.
    :return:  A psycopg2 connection object.
    """

    if db_manager is None:
        init_db_manager()
    return db_manager.get_conn()


def release_db_connection(conn):
    """
    Releases a connection back to the connection pool.
    :param conn: psycopg2 connection object.
    """

    if db_manager is None:
        raise RuntimeError("DB manager is not initialized.")
    db_manager.release_conn(conn)


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
                SELECT followed_id
                FROM follow
                WHERE follower_id = %s
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
                SELECT f1.followed_id
                FROM follow f1
                JOIN follow f2
                  ON f1.followed_id = f2.follower_id
                 AND f1.follower_id = f2.followed_id
                WHERE f1.follower_id = %s
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
                FROM twit p
                WHERE p.author_id IN ({placeholders})
                  AND p.created_at > (NOW() - INTERVAL '24 HOURS')
                  AND p.id NOT IN (
                    SELECT twit_id
                    FROM user_twit
                    WHERE "user_id" = %s
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
                SELECT p.id, COUNT(l.twit_id) AS nb_likes
                from twit  p
                LEFT JOIN \"like\" l ON p.id = l.twit_id
                WHERE p.created_at > (NOW() - INTERVAL '1 HOUR')
                  AND p.id NOT IN (
                    SELECT twit_id
                    FROM user_twit
                    WHERE user_id = %s
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
    Retrieves the IDs of the most popular posts (based on like) published between 1 and 24 hours ago,
    excluding posts the specified user has already viewed.

    :param user_id: ID of the user for whom we want to filter out viewed posts.
    :param limit: Maximum number of post IDs to return.
    :return: A list of (post_id, nb_likes) tuples for unseen posts.
    """

    connection = get_db_connection()
    try:
        with connection.cursor() as cur:
            query = """
                SELECT p.id, COUNT(l.twit_id) AS nb_likes
                from twit  p
                LEFT JOIN \"like\" l ON p.id = l.twit_id
                WHERE p.created_at > (NOW() - INTERVAL '24 HOURS')
                  AND p.created_at < (NOW() - INTERVAL '1 HOUR')
                  AND p.id NOT IN (
                    SELECT twit_id
                    FROM user_twit
                    WHERE user_id = %s
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
                from twit  p
                WHERE p.id NOT IN (
                    SELECT twit_id
                    FROM user_twit
                    WHERE user_id = %s
                )
                ORDER BY p.created_at DESC
                LIMIT %s
            """
            cur.execute(query, (user_id, limit))
            rows = cur.fetchall()
    finally:
        release_db_connection(connection)

    return rows
