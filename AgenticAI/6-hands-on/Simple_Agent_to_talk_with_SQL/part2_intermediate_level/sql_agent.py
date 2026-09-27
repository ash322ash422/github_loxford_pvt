from prompts import SYSTEM_PROMPT

def generate_sql(client, user_question):

    response = client.chat.completions.create(

        model="gpt-4.1-mini",

        messages=[

            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },

            {
                "role": "user",
                "content": user_question
            }

        ],

        temperature=0
    )

    sql_query = response.choices[0].message.content.strip()

    sql_query = sql_query.replace("```sql", "")
    sql_query = sql_query.replace("```", "")
    sql_query = sql_query.strip()

    return sql_query