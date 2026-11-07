import pandas as pd
from datetime import datetime
import os


def save_chat_to_csv(question, answer, session_id=None):

    log_file = "2_chat_history.csv"

    data = {
        "session_id": session_id,
        "timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "question": [question],
        "answer": [answer]
    }

    df = pd.DataFrame(data)

    if os.path.exists(log_file):
        df.to_csv(
            log_file,
            mode="a",
            header=False,
            index=False
        )
    else:
        df.to_csv(
            log_file,
            mode="w",
            header=True,
            index=False
        )