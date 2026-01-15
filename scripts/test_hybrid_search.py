#!/usr/bin/env python3
"""
混合检索功能测试脚本

测试 Lore Agent 的混合检索功能（关键词 + 向量相似度）：
1. 初始化向量存储和 Lore Agent
2. 加载 demo_pack.json 世界包
3. 测试中英文混合查询
4. 显示详细的评分和排名信息
5. 验证关键词优先级和语义理解的结合效果

使用方法:
    python scripts/test_hybrid_search.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.backend.agents.lore import (
    KEYWORD_MATCH_WEIGHT,
    KEYWORD_SECONDARY_WEIGHT,
    VECTOR_MATCH_WEIGHT,
    DUAL_MATCH_BOOST,
    LoreAgent,
)
from src.backend.models.world_pack import WorldPack
from src.backend.services.vector_store import VectorStoreService
from src.backend.services.world import WorldPackLoader


def print_header(title: str) -> None:
    """打印格式化的标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_success(message: str) -> None:
    """打印成功消息"""
    print(f"✅ {message}")


def print_info(message: str) -> None:
    """打印信息消息"""
    print(f"ℹ️  {message}")


def print_error(message: str) -> None:
    """打印错误消息"""
    print(f"❌ {message}")


def print_divider() -> None:
    """打印分隔线"""
    print("-" * 60)


def print_hybrid_result(
    query: str,
    lore_entries: list,
    world_pack,
    show_details: bool = True,
) -> None:
    """
    打印混合检索结果，显示详细的评分信息。

    Args:
        query: 查询文本
        lore_entries: 返回的 lore 条目列表
        world_pack: 世界包实例
        show_details: 是否显示详细信息
    """
    print(f"\n🔍 查询: '{query}'")

    if not lore_entries:
        print("   没有找到结果")
        return

    print(f"   找到 {len(lore_entries)} 条结果\n")

    # 显示每条结果的详细信息
    for i, entry in enumerate(lore_entries, 1):
        print(f"   [{i}] UID: {entry.uid}")
        print(f"       标题: {entry.key[0] if entry.key else 'N/A'}")

        # 显示内容摘要
        content = entry.content.get("cn") or entry.content.get("en", "")
        preview = content[:80] + "..." if len(content) > 80 else content
        print(f"       内容: {preview}")

        # 分析匹配类型
        is_primary_keyword_match = any(
            term in entry.key for term in _extract_search_terms(query)
        )
        has_secondary = hasattr(entry, "secondary_keys") and entry.secondary_keys
        is_secondary_keyword_match = has_secondary and any(
            term in entry.secondary_keys for term in _extract_search_terms(query)
        )

        match_type = []
        if is_primary_keyword_match:
            match_type.append(f"关键词(主要) 权重:{KEYWORD_MATCH_WEIGHT}")
        elif is_secondary_keyword_match:
            match_type.append(f"关键词(次要) 权重:{KEYWORD_SECONDARY_WEIGHT}")
        else:
            match_type.append(f"语义 权重:{VECTOR_MATCH_WEIGHT}")

        print(f"       匹配: {', '.join(match_type)}")
        print()


def _extract_search_terms(query: str) -> list[str]:
    """简单的关键词提取（与 LoreAgent 中的逻辑一致）"""
    import jieba

    stop_words = {
        "的", "了", "是", "在", "我", "你", "他", "她", "它", "有", "没有",
        "什么", "怎么", "如何", "这", "那", "就", "也", "都", "很", "非常",
    }

    terms = []
    words = jieba.lcut(query)

    for word in words:
        clean_word = word.strip("，。！？：；''()（）[]【】\"\"")
        if (clean_word and
            clean_word not in stop_words and
            len(clean_word) > 1 and
            not clean_word.isspace()):
            terms.append(clean_word)

    # 去重并限制数量
    seen = set()
    unique_terms = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            unique_terms.append(term)
            if len(unique_terms) >= 5:
                break

    return unique_terms


async def test_hybrid_search(
    lore_agent,
    world_pack,
    queries: list[str],
    test_name: str,
) -> dict[str, any]:
    """
    测试混合检索并返回统计信息。

    Args:
        lore_agent: Lore Agent 实例
        world_pack: 世界包实例
        queries: 查询列表
        test_name: 测试名称

    Returns:
        统计信息字典
    """
    print_info(f"\n{test_name}")

    stats = {
        "total": 0,
        "keyword_match": 0,
        "semantic_match": 0,
        "correct_rankings": 0,
    }

    for query in queries:
        # 使用 Lore Agent 进行混合搜索
        result = await lore_agent.process({
            "query": query,
            "context": "测试场景",
            "world_pack_id": "demo_pack",
        })

        if result.success:
            entries = []
            # 从返回的内容中提取条目（这里简化处理，实际会从 metadata 中获取）
            # 我们需要重新调用内部方法来获取详细信息
            entries = lore_agent._search_lore(
                world_pack, query, "测试场景", None, None
            )

            stats["total"] += 1

            # 分析第一条结果的匹配类型
            if entries:
                first_entry = entries[0]

                # 检查是否是关键词匹配
                search_terms = _extract_search_terms(query)
                is_keyword_match = any(
                    term in first_entry.key for term in search_terms
                )

                if is_keyword_match:
                    stats["keyword_match"] += 1
                else:
                    stats["semantic_match"] += 1

            print_hybrid_result(query, entries, world_pack, show_details=True)
        else:
            print_error(f"查询失败: {result.error}")

    return stats


async def main():
    """主测试流程"""
    print_header("Lore Agent 混合检索功能测试")

    # 显示当前配置
    print_info("混合检索配置:")
    print(f"   - 关键词匹配权重 (主要): {KEYWORD_MATCH_WEIGHT}")
    print(f"   - 关键词匹配权重 (次要): {KEYWORD_SECONDARY_WEIGHT}")
    print(f"   - 向量相似度权重: {VECTOR_MATCH_WEIGHT}")
    print(f"   - 双重匹配加成: {DUAL_MATCH_BOOST}")

    # =========================================================================
    # 1. 初始化服务
    # =========================================================================
    print_info("\n步骤 1/4: 初始化向量存储服务和 Lore Agent")

    try:
        vector_db_path = project_root / "data" / "test_hybrid_search" / "chroma_db"
        vector_db_path.parent.mkdir(parents=True, exist_ok=True)

        # 清理旧的测试数据
        if vector_db_path.exists():
            import shutil
            shutil.rmtree(vector_db_path)
            print_info("清理旧的测试数据")

        vector_store = VectorStoreService(db_path=vector_db_path)
        print_success("向量存储服务已初始化")
    except Exception as e:
        print_error(f"向量存储初始化失败: {e}")
        return 1

    # =========================================================================
    # 2. 加载世界包并建立索引
    # =========================================================================
    print_info("\n步骤 2/4: 加载世界包并建立向量索引")

    try:
        packs_dir = project_root / "data" / "packs"
        demo_pack_path = packs_dir / "demo_pack.json"

        if not demo_pack_path.exists():
            print_error(f"未找到 demo_pack.json: {demo_pack_path}")
            return 1

        # 使用 WorldPackLoader 加载（启用向量索引）
        world_pack_loader = WorldPackLoader(
            packs_dir=packs_dir,
            vector_store=vector_store,
            enable_vector_indexing=True
        )

        world_pack = world_pack_loader.load("demo_pack")

        print_success(f"世界包已加载: {world_pack.info.name.cn}")
        print_info(f"  版本: {world_pack.info.version}")
        print_info(f"  Lore 条目数: {len(world_pack.entries)}")

        # 为测试创建一个简单的 Lore Agent（不需要 LLM）
        from unittest.mock import MagicMock

        mock_llm = MagicMock()
        lore_agent = LoreAgent(
            llm=mock_llm,
            world_pack_loader=world_pack_loader,
            vector_store=vector_store
        )

        print_success("Lore Agent 已初始化")
    except Exception as e:
        print_error(f"初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # =========================================================================
    # 3. 执行中文查询测试
    # =========================================================================
    print_info("\n步骤 3/4: 执行中文查询测试")

    chinese_queries = [
        ("庄园的历史背景", 1),  # 期望: UID 1 (幽暗庄园)
        ("管家是谁", 3),        # 期望: UID 3 (管家)
        ("密室里有什么", 2),    # 期望: UID 2 (密室)
        ("火灾", 1),           # 期望: UID 1 (庄园) - 包含"火灾"
        ("陈玲", None),        # NPC 名字，期望无匹配或语义相关
    ]

    cn_correct = 0
    cn_total = len(chinese_queries)

    for query, expected_uid in chinese_queries:
        entries = lore_agent._search_lore(
            world_pack, query, "测试场景", None, None
        )

        print_divider()
        print_hybrid_result(query, entries, world_pack)

        if entries and expected_uid is not None:
            if entries[0].uid == expected_uid:
                cn_correct += 1
                print_success(f"   ✅ 正确匹配 UID {expected_uid}")
            else:
                print_error(f"   ❌ 期望 UID {expected_uid}，实际 UID {entries[0].uid}")

    # =========================================================================
    # 4. 执行英文查询测试
    # =========================================================================
    print_info("\n步骤 4/4: 执行英文查询测试")

    english_queries = [
        ("manor history", 1),  # 期望: UID 1 (幽暗庄园)
        ("butler", 3),         # 期望: UID 3 (管家)
        ("secret room", 2),    # 期望: UID 2 (密室)
        ("fire incident", 1),  # 期望: UID 1 或 3 (都包含 fire)
        ("Chen Ling", None),   # NPC 名字，期望无匹配或语义相关
    ]

    en_correct = 0
    en_total = len(english_queries)

    for query, expected_uid in english_queries:
        entries = lore_agent._search_lore(
            world_pack, query, "测试场景", None, None
        )

        print_divider()
        print_hybrid_result(query, entries, world_pack)

        if entries and expected_uid is not None:
            if entries[0].uid == expected_uid:
                en_correct += 1
                print_success(f"   ✅ 正确匹配 UID {expected_uid}")
            else:
                print_error(f"   ❌ 期望 UID {expected_uid}，实际 UID {entries[0].uid}")

    # =========================================================================
    # 总结
    # =========================================================================
    print_header("测试总结")

    total_queries = cn_total + en_total
    total_correct = cn_correct + en_correct
    accuracy = (total_correct / total_queries * 100) if total_queries > 0 else 0

    print(f"中文查询准确率: {cn_correct}/{cn_total} ({cn_correct/cn_total*100:.1f}%)")
    print(f"英文查询准确率: {en_correct}/{en_total} ({en_correct/en_total*100:.1f}%)")
    print(f"总体准确率: {total_correct}/{total_queries} ({accuracy:.1f}%)")

    if accuracy >= 80:
        print_success("混合检索测试通过！准确率 >= 80%")
    elif accuracy >= 60:
        print_info("混合检索基本可用，建议进一步优化")
    else:
        print_error("混合检索需要改进")

    print_info(f"测试数据库位置: {vector_db_path}")
    print_info("提示: 可以手动删除测试数据目录")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
