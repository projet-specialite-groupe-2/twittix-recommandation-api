import random

from .sql import SqlManager


def interleave_posts(friends_posts_id, follows_posts_id, top_hour_posts_id, top_day_posts_id, specific_random, limit):
    """
    Interleaves posts from different sources (friends, follows, and top posts) until 'limit' is reached.

    Actual logic:
    - Takes 1 or 2 posts from friends
    - Takes 1 or 2 posts from follows.
    - Takes 2 to 4 posts from top posts (either 'top_hour_posts' or 'top_day_posts').
    - Repeats this pattern until 'limit' is reached or until the lists are exhausted.

    :param friends_posts_id: List of (post_id,) tuples from friends.
    :param follows_posts_id: List of (post_id,) tuples from followed users.
    :param top_hour_posts_id: List of (post_id, nb_likes) tuples from top posts of the last hour.
    :param top_day_posts_id: List of (post_id, nb_likes) tuples from top posts between 1h and 24h.
    :param specific_random: Random object to use for shuffling and randomizing.
    :param limit: Maximum number of unique post IDs to accumulate.

    :return: A list of post IDs that have been selected.
    """

    recommended_ids = list()

    follows_idx = 0
    friends_idx = 0
    top_hour_idx = 0
    top_day_idx = 0

    while len(recommended_ids) < limit:
        # Add 1 or 2 posts from friends
        recommended_ids, friends_idx = get_some_posts_from_list(friends_idx, friends_posts_id, limit, recommended_ids,
                                                                specific_random,
                                                                1,
                                                                2)

        if len(recommended_ids) >= limit:
            break

        # Add 1 or 2 posts from follows
        recommended_ids, follows_idx = get_some_posts_from_list(follows_idx, follows_posts_id, limit, recommended_ids,
                                                                specific_random,
                                                                1,
                                                                2)

        if len(recommended_ids) >= limit:
            break

        # Add 2 to 4 posts from top posts
        recommended_ids, top_day_idx, top_hour_idx = get_some_top_posts(limit, recommended_ids, top_day_idx,
                                                                        top_day_posts_id, top_hour_idx,
                                                                        top_hour_posts_id, specific_random, 2, 4)

        # If we have reached the end of all lists, stop
        if (top_hour_idx >= len(top_hour_posts_id)
                and top_day_idx >= len(top_day_posts_id)
                and friends_idx >= len(friends_posts_id)):
            break

    return recommended_ids


def get_recommandation(user_id, nbr_posts_to_fetch, specific_random=random.Random()):
    """
    Builds a recommendation for a given user, returning up to 'nbr_posts_to_fetch' unseen post IDs.

    Steps:
    1. Fetch user_follows and user_friends.
    2. Collect unseen posts (<24h) from both lists.
    3. Collect unseen top posts (last hour, last day).
    4. Interleave them with the specified pattern.
    5. If there are not enough recommended posts, fill with the newest unseen posts.

    :param user_id: Integer representing the user ID for which we're building recommendations.
    :param nbr_posts_to_fetch: Integer specifying the maximum number of posts to return.
    :param specific_random: Random object to use for shuffling and randomizing.

    :return: A list of post IDs representing the recommendations.
    """

    user_follows = SqlManager.get_follows(user_id)
    user_friends = SqlManager.get_friends(user_id)

    user_friends_posts_id = SqlManager.get_unseen_24h_posts_id_from_author_ids(user_id, user_friends)
    user_follows_posts_id = SqlManager.get_unseen_24h_posts_id_from_author_ids(user_id, user_follows)
    top_posts_id_last_hour = SqlManager.get_unseen_top_posts_id_last_hour(user_id, nbr_posts_to_fetch)
    top_posts_id_last_day = SqlManager.get_unseen_top_posts_id_last_day_without_last_hour(user_id,
                                                                                          nbr_posts_to_fetch)

    recommended_ids = interleave_posts(
        friends_posts_id=user_friends_posts_id,
        follows_posts_id=user_follows_posts_id,
        top_hour_posts_id=top_posts_id_last_hour,
        top_day_posts_id=top_posts_id_last_day,
        specific_random=specific_random,
        limit=nbr_posts_to_fetch
    )

    if len(recommended_ids) < nbr_posts_to_fetch:
        newest_unseen_posts_id = SqlManager.get_unseen_newest_posts_id(user_id, nbr_posts_to_fetch)
        to_add_index = 0
        while len(recommended_ids) < nbr_posts_to_fetch and to_add_index < len(newest_unseen_posts_id):
            post = newest_unseen_posts_id[to_add_index]
            post_id = post[0]
            if post_id not in recommended_ids:
                recommended_ids.append(post_id)
            to_add_index += 1

    if len(recommended_ids) < nbr_posts_to_fetch:
        newest_posts_id = SqlManager.get_latest_post_ids_excluding(nbr_posts_to_fetch - len(recommended_ids),
                                                                   recommended_ids)
        for post in newest_posts_id:
            post_id = post[0]
            recommended_ids.append(post_id)

    return recommended_ids


def get_some_top_posts(limit, recommended_ids, top_day_idx, top_day_posts, top_hour_idx, top_hour_posts,
                       specific_random, min_nbr_posts,
                       max_nbr_posts):
    """
    Randomly selects between 'min_nbr_posts' and 'max_nbr_posts' post IDs from
    'top_hour_posts' and 'top_day_posts', adding them to 'recommended_ids'.
    Also keeps track of the indexes for both lists and updates them.

    :param limit: Max number of unique post IDs to accumulate.
    :param recommended_ids: List of already selected post IDs.
    :param top_day_idx: Current index for 'top_day_posts'.
    :param top_day_posts: List of (post_id, ...) tuples for top posts from 1h to 24h.
    :param top_hour_idx: Current index for 'top_hour_posts'.
    :param top_hour_posts: List of (post_id, ...) tuples for top posts from the last hour.
    :param specific_random: Random object to use for shuffling and randomizing.
    :param min_nbr_posts: Minimum number of posts to pick in one batch.
    :param max_nbr_posts: Maximum number of posts to pick in one batch.

    :return: (updated_recommended_ids, updated_top_day_idx, updated_top_hour_idx)
    """

    nbr_top_posts_to_add = specific_random.randint(min_nbr_posts, max_nbr_posts)
    nbr_top_posts_add = 0
    while nbr_top_posts_add < nbr_top_posts_to_add:
        if specific_random.random() < 0.5 and top_hour_idx < len(top_hour_posts):
            p = top_hour_posts[top_hour_idx]
            top_hour_idx += 1
        else:
            if top_day_idx < len(top_day_posts):
                p = top_day_posts[top_day_idx]
                top_day_idx += 1
            else:
                if top_hour_idx < len(top_hour_posts):
                    p = top_hour_posts[top_hour_idx]
                    top_hour_idx += 1
                else:
                    break

        if p[0] not in recommended_ids:
            recommended_ids.append(p[0])
            nbr_top_posts_add += 1

        if len(recommended_ids) >= limit:
            break
    return recommended_ids, top_day_idx, top_hour_idx


def get_some_posts_from_list(list_idx, list_posts, limit, recommended_ids, specific_random, min_nbr_posts,
                             max_nbr_posts):
    """
    Randomly selects between 'min_nbr_posts' and 'max_nbr_posts' post IDs from 'list_posts',
    starting at 'list_idx', and adds them to 'recommended_ids'. Returns the updated list and index.

    :param list_idx: Current index in 'list_posts'.
    :param list_posts: List of (post_id,) tuples representing potential posts.
    :param limit: Max number of unique post IDs to accumulate in 'recommended_ids'.
    :param recommended_ids: List of already selected post IDs.
    :param specific_random: Random object to use for shuffling and randomizing.
    :param min_nbr_posts: Minimum number of posts to pick in one batch.
    :param max_nbr_posts: Maximum number of posts to pick in one batch.

    :return: (updated_recommended_ids, updated_list_idx)
    """

    if list_idx < len(list_posts):
        nbr_lists_posts_to_add = specific_random.randint(min_nbr_posts, max_nbr_posts)
        nbr_lists_posts_add = 0
        while list_idx < len(list_posts) and nbr_lists_posts_add < nbr_lists_posts_to_add:
            p = list_posts[list_idx]
            list_idx += 1
            if p[0] not in recommended_ids:
                recommended_ids.append(p[0])
                nbr_lists_posts_add += 1
            if len(recommended_ids) >= limit:
                break

    return recommended_ids, list_idx
