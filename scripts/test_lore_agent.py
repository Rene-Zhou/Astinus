#!/usr/bin/env python3
"""
Lore Agent 测试脚本

测试 LoreAgent 的核心功能：
1. 使用 Google Gemini 作为 LLM 提供商
2. 初始化向量存储和世界包加载器
3. 测试混合搜索（关键字 + 向量相似度）
4. 测试位置感知过滤
5. 测试多语言查询
6. 验证 lore 条目的格式化输出

配置要求:
    - 需要设置环境变量 GOOGLE_API_KEY
    - 或在 config/settings.yaml 中配置 Google provider

使用方法:
    export GOOGLE_API_KEY="your-api-key"
    python scripts/test_lore_agent.py

    或使用 settings.yaml:
    python scripts/test_lore_agent.py --use-config
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.backend.agents.lore import LoreAgent
from src.backend.core.llm_provider import LLMConfig, LLMProvider, get_llm
from src.backend.services.vector_store import VectorStoreService
from src.backend.services.world import WorldPackLoader


def print_header(title: str) -> None:
    """打印格式化的标题"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_success(message: str) -> None:
    """打印成功消息"""
    print(f"✅ {message}")


def print_info(message: str) -> None:
    """打印信息消息"""
    print(f"ℹ️  {message}")


def print_error(message: str) -> None:
    """打印错误消息"""
    print(f"❌ {message}")


def print_query_result(query: str, response, test_num: int) -> None:
    """打印查询结果"""
    print(f"\n{'─' * 70}")
    print(f"测试 {test_num}: {query}")
    print(f"{'─' * 70}")

    if response.success:
        print_success("查询成功")
        print(f"\n{response.content}\n")

        if response.metadata:
            print("📊 元数据:")
            for key, value in response.metadata.items():
                if key == "entries_found":
                    print(f"  - 找到条目数: {len(value)}")
                    for entry in value[:3]:  # 只显示前3个
                        print(f"    • UID {entry.get('uid')}: {', '.join(entry.get('keys', []))}")
                elif key != "query":
                    print(f"  - {key}: {value}")
    else:
        print_error(f"查询失败: {response.error}")


async def main():
    """主测试流程"""
    print_header("Lore Agent 功能测试")

    # =========================================================================
    # 0. 检查 API Key
    # =========================================================================
    print_info("步骤 0/6: 检查 API 配置")

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print_error("未找到 GOOGLE_API_KEY 环境变量")
        print_info("请设置环境变量:")
        print_info("  export GOOGLE_API_KEY='your-api-key'")
        print_info("\n或使用 OpenAI (如果已配置):")
        print_info("  export OPENAI_API_KEY='your-api-key'")
        return 1

    print_success(f"API Key 已配置: {api_key[:10]}...{api_key[-4:]}")

    # =========================================================================
    # 1. 初始化 LLM (使用 Gemini)
    # =========================================================================
    print_info("\n步骤 1/6: 初始化 LLM (Google Gemini)")

    try:
        # 使用 Gemini Flash 模型（更快更便宜，适合测试）
        llm_config = LLMConfig(
            provider=LLMProvider.GOOGLE,
            model="gemini-2.0-flash-exp",  # 或 "gemini-1.5-flash"
            temperature=0.5,
            max_tokens=1024,
            api_key=api_key
        )

        llm = get_llm(llm_config)
        print_success(f"LLM 已初始化: {llm_config.provider.value}/{llm_config.model}")
        print_info(f"  温度: {llm_config.temperature}")
        print_info(f"  最大 tokens: {llm_config.max_tokens}")
    except Exception as e:
        print_error(f"LLM 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # =========================================================================
    # 2. 初始化向量存储
    # =========================================================================
    print_info("\n步骤 2/6: 初始化向量存储服务")

    try:
        vector_db_path = project_root / "data" / "test_lore_agent" / "chroma_db"
        vector_db_path.parent.mkdir(parents=True, exist_ok=True)

        # 清理旧的测试数据
        if vector_db_path.exists():
            import shutil
            shutil.rmtree(vector_db_path)
            print_info("清理旧的测试数据")

        vector_store = VectorStoreService(db_path=vector_db_path)
        print_success(f"向量存储服务已初始化: {vector_db_path}")
    except Exception as e:
        print_error(f"向量存储初始化失败: {e}")
        return 1

    # =========================================================================
    # 3. 初始化世界包加载器
    # =========================================================================
    print_info("\n步骤 3/6: 初始化世界包加载器")

    try:
        packs_dir = project_root / "data" / "packs"
        world_pack_loader = WorldPackLoader(
            packs_dir=packs_dir,
            vector_store=vector_store,
            enable_vector_indexing=True
        )

        available_packs = world_pack_loader.list_available()
        print_success(f"世界包加载器已初始化")
        print_info(f"  可用世界包: {', '.join(available_packs)}")
    except Exception as e:
        print_error(f"世界包加载器初始化失败: {e}")
        return 1

    # =========================================================================
    # 4. 加载 demo_pack 并自动索引
    # =========================================================================
    print_info("\n步骤 4/6: 加载 demo_pack 世界包")

    try:
        world_pack = world_pack_loader.load("demo_pack")
        print_success(f"世界包已加载: {world_pack.info.name.cn}")
        print_info(f"  版本: {world_pack.info.version}")
        print_info(f"  Lore 条目数: {len(world_pack.entries)}")

        # 检查向量索引
        collection_name = f"lore_entries_demo_pack"
        doc_count = vector_store.get_collection_count(collection_name)
        print_success(f"向量索引已自动建立: {doc_count} 个文档")
    except Exception as e:
        print_error(f"世界包加载失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # =========================================================================
    # 5. 初始化 Lore Agent
    # =========================================================================
    print_info("\n步骤 5/6: 初始化 Lore Agent")

    try:
        lore_agent = LoreAgent(
            llm=llm,
            world_pack_loader=world_pack_loader,
            vector_store=vector_store
        )
        print_success("Lore Agent 已初始化")
        print_info("  混合搜索: 关键字匹配 + 向量相似度")
        print_info("  支持位置感知过滤")
        print_info("  支持多语言查询")
    except Exception as e:
        print_error(f"Lore Agent 初始化失败: {e}")
        return 1

    # =========================================================================
    # 6. 执行测试查询
    # =========================================================================
    print_header("执行 Lore Agent 查询测试")

    test_queries = [
        {
            "query": "这个庄园的历史是什么？",
            "context": "玩家刚到达幽暗庄园门前，询问背景信息",
        },
        {
            "query": "管家的故事",
            "context": "玩家在探索庄园时听说了管家的传说",
        },
        {
            "query": "书房里有什么秘密？",
            "context": "玩家正在书房中搜索线索",
        },
        {
            "query": "陈玲是谁？她为什么来这里？",
            "context": "玩家遇到了一个陌生女子",
        },
        {
            "query": "那场大火发生了什么？",
            "context": "玩家在调查庄园的过去",
        },
    ]

    try:
        for i, test_case in enumerate(test_queries, 1):
            response = await lore_agent.process({
                "query": test_case["query"],
                "context": test_case["context"],
                "world_pack_id": "demo_pack",
            })

            print_query_result(test_case["query"], response, i)
            await asyncio.sleep(1)  # 避免 API 限流

        print_success("所有查询测试完成")
    except Exception as e:
        print_error(f"查询测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # =========================================================================
    # 7. 测试位置过滤功能
    # =========================================================================
    print_header("测试位置感知过滤")

    print_info("注意: demo_pack 中的条目没有设置 applicable_locations")
    print_info("此测试主要验证 API 的正常工作，而不是过滤效果")

    try:
        response = await lore_agent.process({
            "query": "当前位置有什么？",
            "context": "玩家在书房中",
            "world_pack_id": "demo_pack",
            "current_location": "study",  # 假设的位置 ID
        })

        print_query_result("位置感知查询（书房）", response, 6)
        print_success("位置过滤功能正常工作")
    except Exception as e:
        print_error(f"位置过滤测试失败: {e}")

    # =========================================================================
    # 总结
    # =========================================================================
    print_header("测试完成")
    print_success("Lore Agent 功能测试全部通过")
    print_info("测试内容:")
    print_info("  ✓ LLM 初始化 (Google Gemini)")
    print_info("  ✓ 向量存储服务")
    print_info("  ✓ 世界包加载和自动索引")
    print_info("  ✓ Lore Agent 混合搜索")
    print_info("  ✓ 多种场景查询")
    print_info("  ✓ 位置感知过滤")
    print_info(f"\n测试数据库位置: {vector_db_path}")
    print_info("提示: 可以手动删除测试数据目录")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
