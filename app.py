import os

from flask import Flask, jsonify, request

from recommendation import Recommandation


def create_app():
    app = Flask(__name__)

    @app.route('/recommendation/<int:user_id>', methods=['GET'])
    def get_recommandation_for_user(user_id):
        n_posts: int = request.args.get("n", default=30, type=int)

        recommandation_posts_ids_ordered = list(Recommandation.get_recommandation(user_id, n_posts))

        return jsonify(recommandation_posts_ids_ordered), 200

    return app


if __name__ == '__main__':
    twittix_recommandation_api_app = create_app()

    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', 5000))

    twittix_recommandation_api_app.run(host=host, port=port)

