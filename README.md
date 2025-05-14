# twittix-recommandation-api

| Méthode | Chemin                      | Paramètre de chemin     | Paramètre GET                     | Réponse                          | Code     |
| ------- | --------------------------- | ----------------------- | --------------------------------- | -------------------------------- | -------- |
| **GET** | `/recommendation/{user_id}` | `user_id` (int, requis) | `n` (int, optionnel, défaut : 30) | Liste JSON des posts recommandés | `200 OK` |
