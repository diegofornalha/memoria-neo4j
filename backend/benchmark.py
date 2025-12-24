#!/usr/bin/env python3
"""
Benchmarks de performance para o módulo save_to_neo4j_secure.

Este script mede performance de validação, conexão e operações de banco.
"""

import asyncio
import time
import tracemalloc
from contextlib import asynccontextmanager
from statistics import mean, median, stdev
from typing import List, Callable, Any

from save_to_neo4j_secure import KnowledgeModel, Neo4jConfig, SecureNeo4jClient


class PerformanceBenchmark:
    """Classe para benchmarks de performance."""

    def __init__(self):
        """Inicializa o benchmark."""
        self.results = {}

    def measure_time(self, func: Callable, *args, **kwargs) -> float:
        """
        Mede o tempo de execução de uma função.

        Args:
            func: Função a ser medida
            *args: Argumentos posicionais
            **kwargs: Argumentos nomeados

        Returns:
            Tempo de execução em segundos
        """
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        return end_time - start_time

    async def measure_async_time(self, coro_func: Callable, *args, **kwargs) -> float:
        """
        Mede o tempo de execução de uma corrotina.

        Args:
            coro_func: Corrotina a ser medida
            *args: Argumentos posicionais
            **kwargs: Argumentos nomeados

        Returns:
            Tempo de execução em segundos
        """
        start_time = time.perf_counter()
        result = await coro_func(*args, **kwargs)
        end_time = time.perf_counter()
        return end_time - start_time

    @asynccontextmanager
    async def measure_memory(self):
        """Context manager para medir uso de memória."""
        tracemalloc.start()
        try:
            yield
        finally:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            print(f"Memória atual: {current / 1024 / 1024:.2f} MB")
            print(f"Pico de memória: {peak / 1024 / 1024:.2f} MB")

    def run_benchmark(self, name: str, func: Callable, iterations: int = 1000) -> dict:
        """
        Executa benchmark de uma função.

        Args:
            name: Nome do benchmark
            func: Função a ser testada
            iterations: Número de iterações

        Returns:
            Resultados estatísticos
        """
        print(f"\nExecutando benchmark: {name}")
        times = []

        for i in range(iterations):
            if i % 100 == 0:
                print(f"  Iteração {i}/{iterations}")

            execution_time = self.measure_time(func)
            times.append(execution_time)

        results = {
            'name': name,
            'iterations': iterations,
            'mean': mean(times),
            'median': median(times),
            'min': min(times),
            'max': max(times),
            'stdev': stdev(times) if len(times) > 1 else 0
        }

        self.results[name] = results
        self._print_results(results)
        return results

    async def run_async_benchmark(self, name: str, coro_func: Callable, iterations: int = 100) -> dict:
        """
        Executa benchmark de uma corrotina.

        Args:
            name: Nome do benchmark
            coro_func: Corrotina a ser testada
            iterations: Número de iterações

        Returns:
            Resultados estatísticos
        """
        print(f"\nExecutando benchmark assíncrono: {name}")
        times = []

        for i in range(iterations):
            if i % 10 == 0:
                print(f"  Iteração {i}/{iterations}")

            execution_time = await self.measure_async_time(coro_func)
            times.append(execution_time)

        results = {
            'name': name,
            'iterations': iterations,
            'mean': mean(times),
            'median': median(times),
            'min': min(times),
            'max': max(times),
            'stdev': stdev(times) if len(times) > 1 else 0
        }

        self.results[name] = results
        self._print_results(results)
        return results

    def _print_results(self, results: dict) -> None:
        """Imprime resultados formatados."""
        print(f"  Resultados para {results['name']}:")
        print(f"    Iterações: {results['iterations']}")
        print(f"    Tempo médio: {results['mean']*1000:.3f} ms")
        print(f"    Mediana: {results['median']*1000:.3f} ms")
        print(f"    Mínimo: {results['min']*1000:.3f} ms")
        print(f"    Máximo: {results['max']*1000:.3f} ms")
        print(f"    Desvio padrão: {results['stdev']*1000:.3f} ms")

    def generate_report(self) -> None:
        """Gera relatório completo dos benchmarks."""
        print("\n" + "="*60)
        print("RELATÓRIO COMPLETO DE PERFORMANCE")
        print("="*60)

        for name, results in self.results.items():
            print(f"\n{name}:")
            print(f"  Throughput: {1/results['mean']:.2f} ops/segundo")
            print(f"  Latência P50: {results['median']*1000:.3f} ms")
            print(f"  Latência P95: {(results['mean'] + 2*results['stdev'])*1000:.3f} ms")


def create_test_knowledge() -> KnowledgeModel:
    """Cria um objeto de conhecimento para testes."""
    return KnowledgeModel(
        name="Test Knowledge for Performance",
        content="This is a test content for performance measurement. " * 50,
        category="Performance",
        tags=["test", "performance", "benchmark", "python", "neo4j"]
    )


def create_large_knowledge() -> KnowledgeModel:
    """Cria um objeto de conhecimento grande para testes."""
    return KnowledgeModel(
        name="Large Knowledge Object",
        content="This is a very large content for testing performance with big data. " * 1000,
        category="Performance",
        tags=[f"tag{i}" for i in range(20)]  # Máximo de tags
    )


async def benchmark_validation():
    """Benchmark de validação de dados."""
    benchmark = PerformanceBenchmark()

    # Teste de validação simples
    benchmark.run_benchmark(
        "Validação Simples",
        lambda: create_test_knowledge(),
        iterations=5000
    )

    # Teste de validação com dados grandes
    benchmark.run_benchmark(
        "Validação Dados Grandes",
        lambda: create_large_knowledge(),
        iterations=1000
    )

    # Teste de validação de labels
    config = Neo4jConfig(
        uri="bolt://localhost:7687",
        username="test",
        password="test"
    )
    client = SecureNeo4jClient(config)

    benchmark.run_benchmark(
        "Validação de Labels",
        lambda: client._validate_label("Learning"),
        iterations=10000
    )

    return benchmark


async def benchmark_memory_usage():
    """Benchmark de uso de memória."""
    print("\n" + "="*40)
    print("BENCHMARK DE MEMÓRIA")
    print("="*40)

    async with PerformanceBenchmark().measure_memory():
        # Criar muitos objetos de conhecimento
        knowledge_objects = []
        for i in range(1000):
            knowledge_objects.append(create_test_knowledge())

        print(f"Criados {len(knowledge_objects)} objetos KnowledgeModel")

        # Validar muitos labels
        config = Neo4jConfig(
            uri="bolt://localhost:7687",
            username="test",
            password="test"
        )
        client = SecureNeo4jClient(config)

        for _ in range(10000):
            client._validate_label("Learning")

        print("Validadas 10,000 labels")


async def benchmark_concurrent_operations():
    """Benchmark de operações concorrentes."""
    print("\n" + "="*40)
    print("BENCHMARK DE CONCORRÊNCIA")
    print("="*40)

    async def create_knowledge_concurrent():
        """Cria conhecimento de forma concorrente."""
        tasks = []
        for _ in range(100):
            task = asyncio.create_task(
                asyncio.to_thread(create_test_knowledge)
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

    benchmark = PerformanceBenchmark()
    await benchmark.run_async_benchmark(
        "Criação Concorrente (100 tasks)",
        create_knowledge_concurrent,
        iterations=10
    )

    return benchmark


async def run_all_benchmarks():
    """Executa todos os benchmarks."""
    print("INICIANDO BENCHMARKS DE PERFORMANCE")
    print("="*60)

    # Benchmark de validação
    validation_benchmark = await benchmark_validation()

    # Benchmark de memória
    await benchmark_memory_usage()

    # Benchmark de concorrência
    concurrency_benchmark = await benchmark_concurrent_operations()

    # Relatório final
    print("\n" + "="*60)
    print("RESUMO FINAL")
    print("="*60)

    validation_benchmark.generate_report()
    concurrency_benchmark.generate_report()

    # Recomendações baseadas nos resultados
    print("\n" + "="*60)
    print("RECOMENDAÇÕES DE PERFORMANCE")
    print("="*60)

    validation_results = validation_benchmark.results.get("Validação Simples", {})
    if validation_results.get('mean', 0) > 0.001:  # > 1ms
        print("⚠️  Validação simples está lenta (>1ms). Considere otimização.")
    else:
        print("✅ Validação simples está performática (<1ms).")

    large_validation = validation_benchmark.results.get("Validação Dados Grandes", {})
    if large_validation.get('mean', 0) > 0.01:  # > 10ms
        print("⚠️  Validação de dados grandes está lenta (>10ms).")
    else:
        print("✅ Validação de dados grandes está aceitável (<10ms).")

    label_validation = validation_benchmark.results.get("Validação de Labels", {})
    if label_validation.get('mean', 0) > 0.0001:  # > 0.1ms
        print("⚠️  Validação de labels pode ser otimizada.")
    else:
        print("✅ Validação de labels está muito rápida (<0.1ms).")


if __name__ == "__main__":
    asyncio.run(run_all_benchmarks())