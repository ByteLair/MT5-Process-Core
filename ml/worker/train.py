import logging
import os

import joblib
import pandas as pd
from sqlalchemy import create_engine

# Configuração de logging estruturado
LOG_DIR = os.environ.get("LOG_DIR", "./logs/ml/")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "train.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# Conexão com o banco e diretório de modelos
# Usa fallback para SQLite em ambiente de testes se DATABASE_URL não estiver definido
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
MODELS_DIR = os.environ.get("MODELS_DIR", "./models")
os.makedirs(MODELS_DIR, exist_ok=True)

# Expor um engine leve em nível de módulo para ser reutilizado pelos testes
engine = create_engine(DB_URL, pool_pre_ping=True, future=True)


def load_dataset(engine_):
    """Carrega o dataset para treino a partir do banco.

    Lança erro se a tabela não existir ou estiver vazia.
    """
    df_local = pd.read_sql(
        """
        SELECT * FROM public.trainset_m1
        WHERE ts >= now() - interval '60 days'
        ORDER BY ts
        """,
        engine_,
    )
    if df_local.empty:
        logging.error("dataset vazio: popula market_data primeiro")
        raise SystemExit("dataset vazio: popula market_data primeiro")
    return df_local


def train_and_save(df_local: pd.DataFrame) -> str:
    """Treina o modelo e salva no diretório configurado, retornando o caminho."""
    X = df_local[
        [
            "close",
            "volume",
            "spread",
            "rsi",
            "macd",
            "macd_signal",
            "macd_hist",
            "atr",
            "ma60",
            "ret_1",
        ]
    ].fillna(0)
    y = (df_local["fwd_ret_5"] > 0).astype(int)

    from sklearn.ensemble import RandomForestClassifier

    m = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    m.fit(X, y)
    path = os.path.join(MODELS_DIR, "rf_m1.pkl")
    joblib.dump(m, path)
    logging.info(f"modelo salvo: {path}")
    print(f"modelo salvo: {path}")
    return path


def main() -> None:
    df_local = load_dataset(engine)
    train_and_save(df_local)


if __name__ == "__main__":
    main()
