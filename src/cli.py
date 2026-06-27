"""
CLI entry point for the medical document ingestion pipeline.

Usage:
    python -m src.cli ingest <path> [options]

See contracts/cli-ingest.md for the full interface specification.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from src.rag.ingestion.data_models import IngestionResult
from src.rag.ingestion.pipeline import ingest_directory, ingest_file
from src.agents.pipeline import ask_langgraph as ask
from src.evaluation.runner import run_evaluation_suite, print_report as print_eval_report


def print_report(result: IngestionResult) -> None:
    """Print a formatted ingestion report to stdout."""
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 Ingestion Report")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Files processed: {result.total_files}")
    print(f"  Successful: {result.success_files}")
    print(f"  Failed: {result.failed_files}")
    print(f"  Total chunks: {result.total_chunks}")
    print(f"  Time elapsed: {result.elapsed_seconds}s")

    if result.errors:
        print()
        print("  ⚠️ Failed files:")
        for err in result.errors:
            print(f"    - {err.file_name}: {err.error_type} — {err.message}")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


def cmd_ingest(args: argparse.Namespace) -> int:
    """Execute the ingest command.

    Returns:
        Exit code: 0 (all success), 1 (some failures), 2 (system error).
    """
    path = args.path
    collection = args.collection
    chunk_size = args.chunk_size
    chunk_overlap = args.chunk_overlap

    try:
        if os.path.isfile(path):
            result = ingest_file(
                file_path=path,
                collection_name=collection,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif os.path.isdir(path):
            result = ingest_directory(
                dir_path=path,
                collection_name=collection,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        else:
            print(f"❌ Error: Path not found: {path}", file=sys.stderr)
            return 2

        print_report(result)

        if result.failed_files > 0 and result.success_files > 0:
            return 1
        elif result.failed_files > 0 and result.success_files == 0:
            return 1
        else:
            return 0

    except ConnectionError as e:
        print(f"❌ System Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"❌ System Error: {e}", file=sys.stderr)
        logging.exception("Unexpected error during ingestion")
        return 2


def cmd_ask(args: argparse.Namespace) -> int:
    """Execute the interactive ask command."""
    print("\n🤖 DiaCareFlow — Hỏi đáp Y khoa về Tiểu đường")
    print("Gõ câu hỏi hoặc 'quit'/'exit' để thoát.\n")
    
    # Optional top_k override from args if added later
    top_k = getattr(args, "top_k", 3)
    
    while True:
        try:
            question = input("> ").strip()
            if not question:
                continue
                
            if question.lower() in ("quit", "exit", "q"):
                print("Tạm biệt!")
                break
                
            # Call pipeline
            answer = ask(question, top_k=top_k)
            
            print("\n📋 Câu trả lời:")
            if answer.is_refused:
                print(f"⚠️ {answer.refuse_reason}")
            else:
                print(answer.text)
                
            if answer.sources:
                print("\n📎 Nguồn:")
                for source in answer.sources:
                    print(f"- {source.source} (score: {source.score:.3f})")
            print()
            
        except KeyboardInterrupt:
            print("\nTạm biệt!")
            break
        except Exception as e:
            print(f"\n❌ Lỗi: {e}")
            logging.exception("Error during Q&A")
            
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Execute the evaluate command."""
    data_path = args.data
    
    if not os.path.isfile(data_path):
        print(f"❌ Error: Test data file not found: {data_path}", file=sys.stderr)
        return 2
        
    try:
        report = run_evaluation_suite(data_path)
        print_eval_report(report)
        return 0 if report.failed_cases == 0 else 1
    except Exception as e:
        print(f"❌ System Error: {e}", file=sys.stderr)
        logging.exception("Unexpected error during evaluation")
        return 2


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="src.cli",
        description="DiaCareFlow — Medical Document Ingestion Pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ingest command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest PDF documents into the RAG knowledge base",
    )
    ingest_parser.add_argument(
        "path",
        type=str,
        help="Path to a PDF file or directory containing PDFs",
    )
    ingest_parser.add_argument(
        "--collection",
        type=str,
        default=None,
        help="Qdrant collection name (default: from config/env)",
    )
    ingest_parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Chunk size in characters (default: 1000)",
    )
    ingest_parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=None,
        help="Overlap between chunks in characters (default: 200)",
    )
    ingest_parser.add_argument(
        "--qdrant-url",
        type=str,
        default=None,
        help="Qdrant server URL (default: http://localhost:6333)",
    )

    # ask command
    ask_parser = subparsers.add_parser(
        "ask",
        help="Interactive Q&A using RAG",
    )
    ask_parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of chunks to retrieve (default: 3)",
    )

    # evaluate command
    eval_parser = subparsers.add_parser(
        "evaluate",
        help="Run system evaluation using sample queries",
    )
    eval_parser.add_argument(
        "--data",
        type=str,
        default="data/test_cases.json",
        help="Path to the JSON file containing test cases (default: data/test_cases.json)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    if args.command == "ingest":
        exit_code = cmd_ingest(args)
        sys.exit(exit_code)
    elif args.command == "ask":
        exit_code = cmd_ask(args)
        sys.exit(exit_code)
    elif args.command == "evaluate":
        exit_code = cmd_evaluate(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
