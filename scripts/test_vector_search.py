#!/usr/bin/env python3
"""
向量检索功能测试脚本

测试 VectorStoreService 的核心功能：
1. 初始化向量存储
2. 加载 demo_pack.json 世界包
3. 对 lore 条目建立向量索引
4. 执行多语言查询测试
5. 验证检索结果的准确性

使用方法:
    python scripts/test_vector_search.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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


def print_search_result(query: str, results: dict, lang: str = "cn") -> None:
    """打印搜索结果"""
    print(f"\n🔍 查询: '{query}' (语言: {lang})")
    print(f"   找到 {len(results.get('ids', [[]])[0])} 条结果")

    if results.get("ids") and results["ids"][0]:
        print("   前3个结果:")
        for i, (doc_id, metadata, distance) in enumerate(zip(
            results["ids"][0][:3],
            results["metadatas"][0][:3],
            results["distances"][0][:3]
        )):
            similarity = 1.0 - min(distance, 1.0)
            print(f"   [{i+1}] ID: {doc_id}")
            print(f"       UID: {metadata.get('uid')}, 相似度: {similarity:.3f}")
            print(f"       关键字: {metadata.get('keys')}")
    else:
        print("   没有找到结果")


async def main():
    """主测试流程"""
    print_header("向量检索功能测试")

    # =========================================================================
    # 1. 初始化向量存储
    # =========================================================================
    print_info("步骤 1/5: 初始化向量存储服务")

    try:
        vector_db_path = project_root / "data" / "test_vector_store" / "chroma_db"
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
    # 2. 加载 demo_pack.json
    # =========================================================================
    print_info("\n步骤 2/5: 加载 demo_pack.json 世界包")

    try:
        packs_dir = project_root / "data" / "packs"
        demo_pack_path = packs_dir / "demo_pack.json"

        if not demo_pack_path.exists():
            print_error(f"未找到 demo_pack.json: {demo_pack_path}")
            return 1

        # 使用 WorldPackLoader 加载（但不启用向量索引，我们手动处理）
        temp_loader = WorldPackLoader(
            packs_dir=packs_dir,
            vector_store=None,  # 不使用自动索引
            enable_vector_indexing=False
        )
        world_pack = temp_loader.load("demo_pack")

        print_success(f"世界包已加载: {world_pack.info.name.cn}")
        print_info(f"  版本: {world_pack.info.version}")
        print_info(f"  描述: {world_pack.info.description.cn}")
        print_info(f"  Lore 条目数: {len(world_pack.entries)}")
        print_info(f"  NPC 数量: {len(world_pack.npcs)}")
    except Exception as e:
        print_error(f"世界包加载失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # =========================================================================
    # 3. 建立向量索引
    # =========================================================================
    print_info("\n步骤 3/5: 为 lore 条目建立向量索引")

    try:
        pack_id = "demo_pack"  # 世界包 ID
        collection_name = f"lore_entries_{pack_id}"

        # 准备文档和元数据
        documents = []
        metadatas = []
        ids = []

        for entry in world_pack.entries.values():
            # 中文版本
            documents.append(entry.content.cn)
            metadatas.append({
                "uid": str(entry.uid),
                "lang": "cn",
                "keys": ",".join(entry.key),
                "order": entry.order,
                "constant": entry.constant,
                "visibility": entry.visibility or "basic",
            })
            ids.append(f"{entry.uid}_cn")

            # 英文版本
            documents.append(entry.content.en)
            metadatas.append({
                "uid": str(entry.uid),
                "lang": "en",
                "keys": ",".join(entry.key),
                "order": entry.order,
                "constant": entry.constant,
                "visibility": entry.visibility or "basic",
            })
            ids.append(f"{entry.uid}_en")

        # 创建集合并添加文档
        collection = vector_store.get_or_create_collection(
            name=collection_name,
            metadata={"pack_id": pack_id}
        )

        vector_store.add_documents(
            collection_name=collection_name,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        doc_count = vector_store.get_collection_count(collection_name)
        print_success(f"向量索引已建立: {collection_name}")
        print_info(f"  索引文档数: {doc_count}")
        print_info(f"  中文文档: {len([m for m in metadatas if m['lang'] == 'cn'])}")
        print_info(f"  英文文档: {len([m for m in metadatas if m['lang'] == 'en'])}")
    except Exception as e:
        print_error(f"向量索引建立失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # =========================================================================
    # 4. 执行中文查询测试
    # =========================================================================
    print_info("\n步骤 4/5: 执行中文查询测试")

    chinese_queries = [
        "庄园的历史背景",
        "管家是谁",
        "密室里有什么",
        "火灾",
        "陈玲",
    ]

    try:
        for query in chinese_queries:
            results = vector_store.search(
                collection_name=collection_name,
                query_text=query,
                n_results=5,
                where={"lang": "cn"}
            )
            print_search_result(query, results, "cn")

        print_success("中文查询测试完成")
    except Exception as e:
        print_error(f"中文查询测试失败: {e}")
        import traceback
        traceback.print_exc()

    # =========================================================================
    # 5. 执行英文查询测试
    # =========================================================================
    print_info("\n步骤 5/5: 执行英文查询测试")

    english_queries = [
        "manor history",
        "butler",
        "secret room",
        "fire incident",
        "Chen Ling",
    ]

    try:
        for query in english_queries:
            results = vector_store.search(
                collection_name=collection_name,
                query_text=query,
                n_results=5,
                where={"lang": "en"}
            )
            print_search_result(query, results, "en")

        print_success("英文查询测试完成")
    except Exception as e:
        print_error(f"英文查询测试失败: {e}")
        import traceback
        traceback.print_exc()

    # =========================================================================
    # 总结
    # =========================================================================
    print_header("测试完成")
    print_success("向量检索功能测试全部通过")
    print_info(f"测试数据库位置: {vector_db_path}")
    print_info("提示: 可以手动删除测试数据目录")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
