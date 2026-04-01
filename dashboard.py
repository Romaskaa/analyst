import json
import os
from typing import Any

import pandas as pd
import streamlit as st

# ------------------------------
# Конфигурация страницы
st.set_page_config(
    page_title="ARS Plus – Панель аналитики",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------
# Заголовок и описание
st.title("📈 ARS Plus – Комплексный анализ данных")
st.markdown(
    "Визуализация результатов SEO-аудита, семантического ядра и сгенерированного контента."
)

# ------------------------------
# Автозагрузка файла all_results.json
json_file = "diocon.json"
data = None

if os.path.exists(json_file):
    try:
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        st.success(f"✅ Файл `{json_file}` успешно загружен автоматически.")
    except Exception as e:
        st.error(f"Ошибка при чтении файла: {e}")
else:
    st.warning(
        f"Файл `{json_file}` не найден в текущей директории. Пожалуйста, загрузите его вручную."
    )
    uploaded = st.file_uploader("Выберите файл JSON", type=["json"])
    if uploaded:
        try:
            data = json.load(uploaded)
            st.success("✅ Файл загружен.")
        except Exception as e:
            st.error(f"Ошибка: {e}")

if data is None:
    st.stop()  # если данных нет, дальше не идём

# ------------------------------
# Боковая панель с навигацией
st.sidebar.header("🔍 Навигация")
sections = [
    "Обзор",
    "Аналитик (специализация и семантика)",
    "AIO (контент, robots, llms)",
    "SEO (проблемы и метрики)",
    "Сгенерированный контент",
    "Исходный JSON",
]
choice = st.sidebar.radio("Перейти к разделу", sections)

# ------------------------------
# Вспомогательные функции


def severity_color(severity: str) -> str:
    """Возвращает цвет для severity."""
    colors = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    return colors.get(severity.lower(), "⚪")


def display_semantic_core(sem_core: dict[str, Any]):
    """Отображает семантическое ядро в трёх колонках."""
    if not sem_core:
        st.info("Нет данных по семантическому ядру")
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 🔴 Высокочастотные")
        hf = sem_core.get("high_frequency", [])
        for item in hf:
            st.markdown(f"- {item}")
    with col2:
        st.markdown("#### 🟡 Среднечастотные")
        mf = sem_core.get("medium_frequency", [])
        for item in mf:
            st.markdown(f"- {item}")
    with col3:
        st.markdown("#### 🟢 Низкочастотные")
        lf = sem_core.get("low_frequency", [])
        for item in lf:
            st.markdown(f"- {item}")


def display_issues(issues: list[dict]):
    """Таблица проблем с цветовой индикацией severity."""
    if not issues:
        st.info("Проблем не обнаружено.")
        return
    df = pd.DataFrame(issues)
    # Добавим столбец с иконкой severity
    df["severity_icon"] = df["severity"].apply(severity_color)
    # Переупорядочим колонки
    cols = ["severity_icon", "title", "severity", "description", "recommendation"]
    df = df[[c for c in cols if c in df.columns]]
    st.dataframe(df, use_container_width=True, hide_index=True)


def display_alt_tags(alt_tags: list):
    """Отображает таблицу alt-тегов."""
    if not alt_tags:
        st.info("Нет alt-тегов")
        return
    # alt_tags может быть списком списков, распрямим
    flat = []
    for group in alt_tags:
        if isinstance(group, list):
            flat.extend(group)
        else:
            flat.append(group)
    if flat:
        df = pd.DataFrame(flat)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Нет alt-тегов")


def clean_code(text: str) -> str:
    """Убирает обрамляющие ``` из текста."""
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
    return text


def metric_card(label, value, help=None):
    """Стилизованная метрика."""
    st.metric(label, value, help=help)


# ------------------------------
# ОСНОВНОЙ ИНТЕРФЕЙС

if choice == "Обзор":
    st.header("📋 Общая информация")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("URL", data.get("url", "—"))
    with col2:
        metric_card("Всего токенов", f"{data.get('total_tokens', 0):,}")
    with col3:
        metric_card("Затраты (руб)", f"{data.get('total_money', 0):.2f}")
    with col4:
        rag = data.get("rag_result", "—")
        metric_card("RAG результат", rag)

    # Краткая сводка по направлениям из analyst_result
    analyst = data.get("analyst_result", {})
    if analyst:
        st.subheader("🧠 Основные направления")
        spec = analyst.get("specialization", {}).get("specialization", "")
        if spec:
            st.info(spec)

elif choice == "Аналитик (специализация и семантика)":
    st.header("🧠 Результат аналитика")
    analyst = data.get("analyst_result", {})
    if not analyst:
        st.warning("Нет данных")
    else:
        with st.expander("📌 Специализация", expanded=True):
            st.write(analyst.get("specialization", {}).get("specialization", "—"))

        with st.expander("🎯 Экспертиза", expanded=True):
            exp = analyst.get("expertise", {})
            if exp:
                st.markdown(f"**Основное направление:** {exp.get('main_area', '—')}")
                st.markdown(
                    f"**Ключевая проблема пользователя:** {exp.get('key_user_problem', '—')}"
                )
                st.markdown(f"**Польза для пользователя:** {exp.get('benefit_to_the_user', '—')}")
            else:
                st.write("Нет данных")

        with st.expander("🔑 Семантическое ядро", expanded=True):
            display_semantic_core(analyst.get("semantic_core", {}))

elif choice == "AIO (контент, robots, llms)":
    st.header("🤖 Результат AIO")
    aio = data.get("aio_result", {})
    if not aio:
        st.warning("Нет данных")
    else:
        with st.expander("📝 Новый контент", expanded=True):
            nc = aio.get("new_content", {})
            st.markdown(nc.get("transformed_content", "—"))
            st.markdown("**Рекомендации по размещению:**")
            st.info(nc.get("placement_recommendation", "—"))

        with st.expander("🤖 robots.txt"):
            robots = aio.get("robots_txt", "")
            if robots:
                st.code(clean_code(robots), language="text")
            else:
                st.write("Нет данных")

        with st.expander("📄 llms.txt"):
            llms = aio.get("llms_txt", "")
            if llms:
                st.code(clean_code(llms), language="text")
            else:
                st.write("Нет данных")

        with st.expander("🔗 JSON-LD"):
            json_ld = aio.get("json_ld", "—")
            st.json(json_ld) if isinstance(json_ld, dict) else st.write(json_ld)

elif choice == "SEO (проблемы и метрики)":
    st.header("🔎 SEO анализ")
    seo = data.get("seo_result", {})
    if not seo:
        st.warning("Нет данных")
    else:
        # Сводка
        st.subheader("Общая сводка")
        st.write(seo.get("overall_summary", "—"))

        # Метрики производительности
        perf = seo.get("performance", {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_card("SEO оценка", f"{seo.get('seo', {}).get('score', '—')}/100")
        with col2:
            metric_card("Performance", f"{perf.get('score', '—')}/100")
        with col3:
            metric_card("LCP (с)", perf.get("lcp", "—"))
        with col4:
            metric_card("CLS", perf.get("cls", "—"))

        # Проблемы
        st.subheader("⚠️ Проблемы")
        issues = seo.get("issues", [])
        display_issues(issues)

        # Рекомендации
        st.subheader("✅ Рекомендации")
        recs = seo.get("recommendations", [])
        if recs:
            for i, r in enumerate(recs, 1):
                st.markdown(f"{i}. {r}")
        else:
            st.write("Нет рекомендаций")

        # Детальные анализы
        with st.expander("📊 Анализ контента"):
            st.write(seo.get("content_analysis", "—"))
        with st.expander("🌐 Core Web Vitals"):
            st.write(seo.get("core_web_vitals_analysis", "—"))

elif choice == "Сгенерированный контент":
    st.header("📝 Сгенерированный контент")
    cont = data.get("conent_generation_result", {})  # опечатка в ключе
    if not cont:
        st.warning("Нет данных")
    else:
        st.subheader("Мета-информация")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**URL:** {cont.get('url', '—')}")
            st.markdown(f"**Title:** {cont.get('title', '—')}")
            st.markdown(f"**H1:** {cont.get('h1', '—')}")
        with col2:
            st.markdown(f"**Description:** {cont.get('description', '—')}")

        st.subheader("🖼️ Alt-теги изображений")
        alt_tags = cont.get("alt_tags", [])
        display_alt_tags(alt_tags)

else:  # Исходный JSON
    st.header("📦 Исходные данные JSON")
    st.json(data)

# ------------------------------
# Футер
st.markdown("---")
st.caption("📊 Визуализатор данных ARS Plus • Сделано на Streamlit")
