"""
OpenTelemetry Tracing Configuration for Jaeger
Configura instrumentação automática e manual de traces
"""
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def setup_tracing(app, service_name: str = "mt5-trading-api", service_version: str = "1.0.0"):
    """
    Configura OpenTelemetry tracing com Jaeger
    
    Args:
        app: FastAPI application instance
        service_name: Nome do serviço para identificação no Jaeger
        service_version: Versão do serviço
    """
    # Verificar se tracing está habilitado
    jaeger_enabled = os.getenv("JAEGER_ENABLED", "true").lower() == "true"
    if not jaeger_enabled:
        logger.info("Jaeger tracing is disabled")
        return None
    
    # Configuração do Jaeger endpoint
    jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")
    
    try:
        # Definir resource com informações do serviço
        resource = Resource(attributes={
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
            "host.name": os.getenv("HOSTNAME", "unknown"),
        })
        
        # Configurar TracerProvider
        provider = TracerProvider(resource=resource)
        
        # Configurar exportador OTLP para Jaeger
        otlp_exporter = OTLPSpanExporter(
            endpoint=jaeger_endpoint,
            insecure=True  # Em produção, usar TLS
        )
        
        # Adicionar span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(span_processor)
        
        # Definir como provider global
        trace.set_tracer_provider(provider)
        
        # Instrumentar FastAPI automaticamente
        FastAPIInstrumentor.instrument_app(app)
        
        logger.info(f"✓ Jaeger tracing initialized: {jaeger_endpoint}")
        logger.info(f"  Service: {service_name} v{service_version}")
        
        return provider
        
    except Exception as e:
        logger.error(f"Failed to initialize Jaeger tracing: {e}")
        return None


def instrument_sqlalchemy(engine):
    """
    Instrumenta SQLAlchemy engine para tracing de queries
    
    Args:
        engine: SQLAlchemy engine instance
    """
    try:
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,
            commenter_options={}
        )
        logger.info("✓ SQLAlchemy instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument SQLAlchemy: {e}")


def get_tracer(name: str = __name__):
    """
    Obtém um tracer para criar spans manualmente
    
    Args:
        name: Nome do tracer (geralmente __name__ do módulo)
    
    Returns:
        Tracer instance
    
    Usage:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("operation_name"):
            # seu código aqui
            pass
    """
    return trace.get_tracer(name)


def add_span_attributes(span, **attributes):
    """
    Adiciona atributos customizados a um span
    
    Args:
        span: Span ativo
        **attributes: Pares chave-valor para adicionar ao span
    
    Usage:
        span = trace.get_current_span()
        add_span_attributes(span, user_id=123, symbol="EURUSD")
    """
    if span is not None and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_span_event(span, name: str, attributes: Optional[dict] = None):
    """
    Adiciona um evento ao span atual
    
    Args:
        span: Span ativo
        name: Nome do evento
        attributes: Atributos adicionais do evento
    
    Usage:
        span = trace.get_current_span()
        add_span_event(span, "cache_hit", {"cache_key": "symbols_list"})
    """
    if span is not None and span.is_recording():
        span.add_event(name, attributes=attributes or {})


def record_exception(span, exception: Exception):
    """
    Registra uma exceção no span
    
    Args:
        span: Span ativo
        exception: Exceção capturada
    
    Usage:
        try:
            # operação
            pass
        except Exception as e:
            span = trace.get_current_span()
            record_exception(span, e)
            raise
    """
    if span is not None and span.is_recording():
        span.record_exception(exception)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))


# Decorator para criar spans automaticamente
def traced(span_name: Optional[str] = None):
    """
    Decorator para adicionar tracing automático a funções
    
    Args:
        span_name: Nome customizado do span (default: nome da função)
    
    Usage:
        @traced("process_signal")
        def process_trading_signal(symbol, timeframe):
            # seu código aqui
            pass
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            name = span_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(name) as span:
                # Adicionar argumentos como atributos
                if args:
                    span.set_attribute("args", str(args[:3]))  # Primeiros 3 args
                if kwargs:
                    for key, value in list(kwargs.items())[:5]:  # Primeiros 5 kwargs
                        span.set_attribute(f"arg.{key}", str(value)[:100])
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    record_exception(span, e)
                    raise
        
        return wrapper
    return decorator


# Contexto para criar spans manualmente
class TracedContext:
    """
    Context manager para criar spans customizados
    
    Usage:
        with TracedContext("database_query", {"table": "ohlc_data"}):
            # operação
            pass
    """
    def __init__(self, span_name: str, attributes: Optional[dict] = None):
        self.span_name = span_name
        self.attributes = attributes or {}
        self.tracer = get_tracer()
        self.span = None
    
    def __enter__(self):
        self.span = self.tracer.start_as_current_span(self.span_name)
        self.span.__enter__()
        
        # Adicionar atributos
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            record_exception(self.span, exc_val)
        
        self.span.__exit__(exc_type, exc_val, exc_tb)
        return False
