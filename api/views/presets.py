PLANTACIONES_PRESETS = {
    'Lechuga': {
        'semanas_ciclo': 5,
        'reglas': {
            'TEMP': (18.0, 22.0),
            'PH': (5.5, 6.2),
            'AGUA': (70.0, 100.0),
            'NUT_A': (1.5, 2.5),
            'NUT_B': (1.5, 2.5),
        },
    },
    'Acelga': {
        'semanas_ciclo': 7,
        'reglas': {
            'TEMP': (16.0, 22.0),
            'PH': (6.0, 6.5),
            'AGUA': (70.0, 100.0),
            'NUT_A': (2.0, 3.0),
            'NUT_B': (2.0, 3.0),
        },
    },
    'Hierbabuena': {
        'semanas_ciclo': 6,
        'reglas': {
            'TEMP': (18.0, 24.0),
            'PH': (5.8, 6.5),
            'AGUA': (70.0, 100.0),
            'NUT_A': (1.8, 2.6),
            'NUT_B': (1.8, 2.6),
        },
    },
    'Cilantro': {
        'semanas_ciclo': 4,
        'reglas': {
            'TEMP': (17.0, 23.0),
            'PH': (6.0, 6.7),
            'AGUA': (65.0, 100.0),
            'NUT_A': (1.5, 2.2),
            'NUT_B': (1.5, 2.2),
        },
    },
    'Perejil': {
        'semanas_ciclo': 8,
        'reglas': {
            'TEMP': (16.0, 22.0),
            'PH': (5.5, 6.5),
            'AGUA': (70.0, 100.0),
            'NUT_A': (1.6, 2.4),
            'NUT_B': (1.6, 2.4),
        },
    },
    'Kale': {
        'semanas_ciclo': 8,
        'reglas': {
            'TEMP': (15.0, 21.0),
            'PH': (5.8, 6.5),
            'AGUA': (70.0, 100.0),
            'NUT_A': (2.0, 3.2),
            'NUT_B': (2.0, 3.2),
        },
    },
    'Menta': {
        'semanas_ciclo': 6,
        'reglas': {
            'TEMP': (18.0, 24.0),
            'PH': (5.8, 6.5),
            'AGUA': (70.0, 100.0),
            'NUT_A': (1.8, 2.6),
            'NUT_B': (1.8, 2.6),
        },
    },
    'Brócoli': {
        'semanas_ciclo': 10,
        'reglas': {
            'TEMP': (15.0, 20.0),
            'PH': (6.0, 6.8),
            'AGUA': (75.0, 100.0),
            'NUT_A': (2.5, 3.8),
            'NUT_B': (2.5, 3.8),
        },
    },
    'Albahaca': {
        'semanas_ciclo': 6,
        'reglas': {
            'TEMP': (20.0, 25.0),
            'PH': (5.5, 6.5),
            'AGUA': (70.0, 100.0),
            'NUT_A': (1.8, 2.8),
            'NUT_B': (1.8, 2.8),
        },
    },
    'Apio': {
        'semanas_ciclo': 10,
        'reglas': {
            'TEMP': (16.0, 21.0),
            'PH': (6.0, 6.5),
            'AGUA': (75.0, 100.0),
            'NUT_A': (2.0, 3.0),
            'NUT_B': (2.0, 3.0),
        },
    },
    'Tomate-Cherry': {
        'semanas_ciclo': 12,
        'reglas': {
            'TEMP': (20.0, 26.0),
            'PH': (5.8, 6.5),
            'AGUA': (75.0, 100.0),
            'NUT_A': (3.0, 4.5),
            'NUT_B': (3.0, 4.5),
        },
    },
}


def obtener_especie_base(tipo_planta):
    """Mapea variedades (ej. 'Lechuga Milanesa') a su especie base en PLANTACIONES_PRESETS."""
    if not tipo_planta:
        return ''
    nombre = tipo_planta.strip()
    if nombre.startswith('Lechuga'):
        return 'Lechuga'
    if nombre.startswith('Acelga'):
        return 'Acelga'
    return nombre


def aplicar_preset_a_cultivo(cultivo):
    """Crea o actualiza las 5 reglas de umbral según el tipo de planta o su especie base."""
    from ..models import ReglaUmbral

    especie_base = obtener_especie_base(cultivo.tipo_planta)
    preset = PLANTACIONES_PRESETS.get(especie_base)
    if not preset:
        return

    cultivo.semanas_ciclo = preset['semanas_ciclo']
    cultivo.save(update_fields=['semanas_ciclo'])

    for variable, (minimo, maximo) in preset['reglas'].items():
        ReglaUmbral.objects.update_or_create(
            cultivo=cultivo,
            variable=variable,
            defaults={'rango_minimo': minimo, 'rango_maximo': maximo},
        )