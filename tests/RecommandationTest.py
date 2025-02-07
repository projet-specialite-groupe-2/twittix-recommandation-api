import unittest
from unittest.mock import patch
import random

from recommendation.Recommandation import get_recommandation, interleave_posts


class TestRecommandation(unittest.TestCase):

    @patch('recommendation.sql.SqlManager.get_follows')
    @patch('recommendation.sql.SqlManager.get_friends')
    @patch('recommendation.sql.SqlManager.get_unseen_24h_posts_id_from_author_ids')
    @patch('recommendation.sql.SqlManager.get_unseen_top_posts_id_last_hour')
    @patch('recommendation.sql.SqlManager.get_unseen_top_posts_id_last_day_without_last_hour')
    @patch('recommendation.sql.SqlManager.get_unseen_newest_posts_id')
    def test_get_recommandation_basic(
        self,
        mock_get_newest,
        mock_get_top_day,
        mock_get_top_hour,
        mock_get_24h_authors,
        mock_get_friends,
        mock_get_follows
    ):
        """
        Test basic flow where we have some data from friends, follows, top hour, top day,
        and we want to see if the final recommendation merges them up to the limit.
        """

        mock_get_follows.return_value = [2, 3, 4]
        mock_get_friends.return_value = [4]
        mock_get_24h_authors.side_effect = [
            [(101,)],  # user_friends (authors = [4])
            [(101,), (201,), (202,)]   # user_follows (authors= [2, 3, 4])
        ]
        mock_get_top_hour.return_value = [(301, 5), (302, 3)]
        mock_get_top_day.return_value = [(401, 10), (402, 8), (403, 1)]
        mock_get_newest.return_value = [(501,), (502,), (503,), (504,)]

        recommended = get_recommandation(
            user_id=1,
            nbr_posts_to_fetch=5
        )

        self.assertEqual(len(recommended), 5)
        self.assertIn(101, recommended)
        self.assertIn(201, recommended)

    @patch('recommendation.sql.SqlManager.get_follows', return_value=[])
    @patch('recommendation.sql.SqlManager.get_friends', return_value=[])
    @patch('recommendation.sql.SqlManager.get_unseen_24h_posts_id_from_author_ids', return_value=[])
    @patch('recommendation.sql.SqlManager.get_unseen_top_posts_id_last_hour', return_value=[])
    @patch('recommendation.sql.SqlManager.get_unseen_top_posts_id_last_day_without_last_hour', return_value=[])
    @patch('recommendation.sql.SqlManager.get_unseen_newest_posts_id', return_value=[(601,), (602,), (603,)])
    def test_get_recommandation_all_empty(self,
        mock_get_newest,
        mock_get_top_day,
        mock_get_top_hour,
        mock_get_24h_authors,
        mock_get_friends,
        mock_get_follows
    ):
        """
        Test the case where there's no data in any of the 24h/follows/friends/top
        and only 'newest' is available.
        """
        recommended = get_recommandation(
            user_id=1,
            nbr_posts_to_fetch=5
        )

        self.assertEqual(len(recommended), 3)
        self.assertListEqual(recommended, [601, 602, 603])


    def test_interleave_posts_simple(self):
        """
        Test the interleave function directly, controlling the input lists
        and verifying the final order of recommended IDs.
        """
        friends_posts_id = [(101,), (102,), (103,)]
        follows_posts_id = [(201,), (202,)]
        top_hour_posts_id = [(301, 4), (302, 2)]
        top_day_posts_id = [(401, 10), (402, 5)]
        specific_random = random.Random(0)
        limit = 5

        result = interleave_posts(
            friends_posts_id,
            follows_posts_id,
            top_hour_posts_id,
            top_day_posts_id,
            specific_random,
            limit
        )

        self.assertLessEqual(len(result), 5)
        for post_id in [101, 102, 201, 202, 301]:
            self.assertIn(post_id, result)


if __name__ == '__main__':
    unittest.main()
