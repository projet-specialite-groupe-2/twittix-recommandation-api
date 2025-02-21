import os

from flask import Flask, jsonify

from recommendation import Recommandation
from recommendation.sql import SqlManager


def create_app():
    app = Flask(__name__)

    @app.route('/recommendation/<int:user_id>', methods=['GET'])
    def get_recommandation_for_user(user_id):
        recommandation_posts_ids_ordered = list(Recommandation.get_recommandation(user_id, 30))

        recommandation_posts = SqlManager.get_posts_by_id_list(recommandation_posts_ids_ordered)
        recommandation_posts_dict = {post["id"]: post for post in recommandation_posts}
        recommandation_posts_ordered = [
            recommandation_posts_dict[pid]
            for pid in recommandation_posts_ids_ordered
            if pid in recommandation_posts_dict
        ]

        SqlManager.mark_posts_as_viewed(user_id, recommandation_posts_ids_ordered)

        return jsonify(recommandation_posts_ordered), 200

    return app


if __name__ == '__main__':
    twittix_recommandation_api_app = create_app()

    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', 5000))

    twittix_recommandation_api_app.run(host=host, port=port)

