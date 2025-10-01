"""
CLI principal para consultas RAG con AWS Bedrock
"""
import sys
import logging
from pathlib import Path
from typing import List

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..shared.models import QueryRequest
from ..shared.document_processor import DocumentProcessor
from ..shared.utils import setup_logging, format_file_size
from .config import get_bedrock_config, get_log_level
from .bedrock_client import BedrockClient

console = Console()
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """CLI para consultas RAG con AWS Bedrock y Claude"""
    pass


@cli.command()
@click.option(
    "--prompt", "-p",
    required=True,
    help="Pregunta o prompt para el modelo"
)
@click.option(
    "--files", "-f",
    multiple=True,
    type=click.Path(exists=True),
    help="Archivos a incluir en la consulta (PDF, imágenes, Excel, Word, texto)"
)
@click.option(
    "--max-tokens",
    type=int,
    default=None,
    help="Máximo de tokens en la respuesta"
)
@click.option(
    "--temperature",
    type=float,
    default=None,
    help="Temperatura del modelo (0.0 - 1.0)"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Modo verbose (muestra logs detallados)"
)
def query(prompt: str, files: tuple, max_tokens: int, temperature: float, verbose: bool):
    """
    Realiza una consulta al modelo LLM con documentos adjuntos
    
    Ejemplo:
        python -m src.cli.main query -p "Resume estos documentos" -f doc1.pdf -f imagen.jpg
    """
    # Configurar logging
    log_level = "DEBUG" if verbose else get_log_level()
    setup_logging(log_level)
    
    try:
        # Mostrar banner
        console.print(Panel.fit(
            "[bold cyan]Consulta RAG con AWS Bedrock[/bold cyan]\n"
            "[dim]Claude 3.5 Sonnet[/dim]",
            border_style="cyan"
        ))
        
        # Obtener configuración
        config = get_bedrock_config()
        
        # Sobrescribir con parámetros CLI si se proporcionan
        if max_tokens:
            config.max_tokens = max_tokens
        if temperature is not None:
            config.temperature = temperature
        
        console.print(f"\n[bold]Configuración:[/bold]")
        console.print(f"  Región: [cyan]{config.region}[/cyan]")
        console.print(f"  Modelo: [cyan]{config.model_id}[/cyan]")
        console.print(f"  Max tokens: [cyan]{config.max_tokens}[/cyan]")
        console.print(f"  Temperature: [cyan]{config.temperature}[/cyan]")
        
        # Procesar documentos
        documents = []
        if files:
            console.print(f"\n[bold]Procesando {len(files)} archivo(s)...[/bold]")
            processor = DocumentProcessor()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Procesando documentos...", total=len(files))
                
                for file_path in files:
                    try:
                        doc = processor.process_document(str(file_path))
                        documents.append(doc)
                        console.print(f"  ✓ {doc.file_name} ({format_file_size(doc.size_bytes)}) - {doc.document_type}")
                        progress.advance(task)
                    except Exception as e:
                        console.print(f"  [red]✗ Error procesando {file_path}: {str(e)}[/red]")
                        progress.advance(task)
        
        # Crear solicitud
        request = QueryRequest(
            prompt=prompt,
            documents=documents,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
        
        # Inicializar cliente Bedrock
        console.print(f"\n[bold]Conectando con AWS Bedrock...[/bold]")
        client = BedrockClient(config)
        
        # Realizar consulta
        console.print(f"\n[bold]Enviando consulta...[/bold]")
        console.print(f"[dim]Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}[/dim]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Esperando respuesta del modelo...", total=None)
            response = client.invoke_model(request)
        
        # Mostrar respuesta
        console.print("\n" + "="*80 + "\n")
        console.print(Panel(
            Markdown(response.response),
            title="[bold green]Respuesta de Claude[/bold green]",
            border_style="green"
        ))
        
        # Mostrar estadísticas
        console.print(f"\n[bold]Estadísticas:[/bold]")
        console.print(f"  Tokens entrada: [cyan]{response.input_tokens}[/cyan]")
        console.print(f"  Tokens salida: [cyan]{response.output_tokens}[/cyan]")
        console.print(f"  Total tokens: [cyan]{response.input_tokens + response.output_tokens}[/cyan]")
        console.print(f"  Razón de parada: [cyan]{response.stop_reason}[/cyan]")
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        if verbose:
            logger.exception("Error detallado:")
        sys.exit(1)


@cli.command()
def test():
    """
    Prueba la conexión con AWS Bedrock
    """
    setup_logging(get_log_level())
    
    try:
        console.print(Panel.fit(
            "[bold cyan]Test de Conexión AWS Bedrock[/bold cyan]",
            border_style="cyan"
        ))
        
        config = get_bedrock_config()
        console.print(f"\n[bold]Configuración:[/bold]")
        console.print(f"  Región: [cyan]{config.region}[/cyan]")
        console.print(f"  Modelo: [cyan]{config.model_id}[/cyan]")
        
        console.print(f"\n[bold]Probando conexión...[/bold]")
        client = BedrockClient(config)
        
        if client.test_connection():
            console.print("\n[bold green]✓ Conexión exitosa con AWS Bedrock[/bold green]")
        else:
            console.print("\n[bold red]✗ Error en la conexión[/bold red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True))
def validate(files: tuple):
    """
    Valida archivos antes de enviarlos al modelo
    
    Ejemplo:
        python -m src.cli.main validate doc1.pdf imagen.jpg datos.xlsx
    """
    setup_logging(get_log_level())
    
    if not files:
        console.print("[yellow]No se proporcionaron archivos para validar[/yellow]")
        return
    
    console.print(Panel.fit(
        "[bold cyan]Validación de Archivos[/bold cyan]",
        border_style="cyan"
    ))
    
    processor = DocumentProcessor()
    
    console.print(f"\n[bold]Validando {len(files)} archivo(s)...[/bold]\n")
    
    valid_count = 0
    invalid_count = 0
    
    for file_path in files:
        try:
            doc = processor.process_document(str(file_path))
            console.print(f"[green]✓[/green] {doc.file_name}")
            console.print(f"  Tipo: {doc.document_type}")
            console.print(f"  Tamaño: {format_file_size(doc.size_bytes)}")
            console.print(f"  MIME: {doc.mime_type}")
            valid_count += 1
        except Exception as e:
            console.print(f"[red]✗[/red] {Path(file_path).name}")
            console.print(f"  Error: {str(e)}")
            invalid_count += 1
        console.print()
    
    # Resumen
    console.print("[bold]Resumen:[/bold]")
    console.print(f"  Válidos: [green]{valid_count}[/green]")
    console.print(f"  Inválidos: [red]{invalid_count}[/red]")


if __name__ == "__main__":
    cli()
