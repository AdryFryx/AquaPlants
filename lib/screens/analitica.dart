import 'package:flutter/material.dart';
import 'package:aquaplants/services/api_service.dart';

class AnaliticaScreen extends StatefulWidget {
  const AnaliticaScreen({super.key});

  @override
  State<AnaliticaScreen> createState() => _AnaliticaScreenState();
}

class _AnaliticaScreenState extends State<AnaliticaScreen> {
  final ApiService _apiService = ApiService();

  int _diasSeleccionados = 7;
  String _tituloPeriodo = 'Resumen Semanal';
  bool _isLoading = true;

  // Selector de plantaciones
  List<dynamic> _cultivos = [];
  Map<String, dynamic>? _cultivoSeleccionado;

  // Métricas calculadas
  int _totalMediciones = 0;
  double? _tempProm;
  double? _aguaProm;
  double? _phProm;
  double? _nutAProm;
  double? _nutBProm;
  double _porcentajeEstabilidad = 0.0;

  @override
  void initState() {
    super.initState();
    _inicializarAnalitica();
  }

  Future<void> _inicializarAnalitica() async {
    final cultivos = await _apiService.getMisCultivos();
    if (mounted) {
      setState(() {
        _cultivos = cultivos;
        if (_cultivos.isNotEmpty) {
          _cultivoSeleccionado = _cultivos.first;
        }
      });
    }
    await _cargarEstadisticas();
  }

  Future<void> _cargarEstadisticas() async {
    if (mounted) setState(() => _isLoading = true);

    final int? dispositivoId = _cultivoSeleccionado?['dispositivo_id'];
    final datos = await _apiService.getMediciones(
      dias: _diasSeleccionados,
      dispositivoId: dispositivoId,
    );

    if (!mounted) return;

    if (datos.isEmpty) {
      setState(() {
        _totalMediciones = 0;
        _tempProm = _aguaProm = _phProm = _nutAProm = _nutBProm = null;
        _porcentajeEstabilidad = 0.0;
        _isLoading = false;
      });
      return;
    }

    double sumTemp = 0, sumAgua = 0, sumPh = 0, sumNutA = 0, sumNutB = 0;
    int cTemp = 0, cAgua = 0, cPh = 0, cNutA = 0, cNutB = 0;

    int evaluacionesTotales = 0;
    int evaluacionesEnRango = 0;

    final reglas = _cultivoSeleccionado?['reglas'] as Map<String, dynamic>? ?? {};

    void evaluarRegla(String clave, double valor) {
      final regla = reglas[clave];
      if (regla == null) return;
      final min = (regla['minimo'] as num).toDouble();
      final max = (regla['maximo'] as num).toDouble();
      evaluacionesTotales++;
      if (valor >= min && valor <= max) {
        evaluacionesEnRango++;
      }
    }

    for (final m in datos) {
      final t = (m['temperatura'] as num?)?.toDouble();
      final a = (m['nivel_agua'] as num?)?.toDouble();
      final p = (m['ph'] as num?)?.toDouble();
      final na = (m['nutriente_a'] as num?)?.toDouble();
      final nb = (m['nutriente_b'] as num?)?.toDouble();

      if (t != null) { sumTemp += t; cTemp++; evaluarRegla('TEMP', t); }
      if (a != null) { sumAgua += a; cAgua++; evaluarRegla('AGUA', a); }
      if (p != null) { sumPh += p; cPh++; evaluarRegla('PH', p); }
      if (na != null) { sumNutA += na; cNutA++; evaluarRegla('NUT_A', na); }
      if (nb != null) { sumNutB += nb; cNutB++; evaluarRegla('NUT_B', nb); }
    }

    setState(() {
      _totalMediciones = datos.length;
      _tempProm = cTemp > 0 ? sumTemp / cTemp : null;
      _aguaProm = cAgua > 0 ? sumAgua / cAgua : null;
      _phProm = cPh > 0 ? sumPh / cPh : null;
      _nutAProm = cNutA > 0 ? sumNutA / cNutA : null;
      _nutBProm = cNutB > 0 ? sumNutB / cNutB : null;
      _porcentajeEstabilidad = evaluacionesTotales > 0
          ? (evaluacionesEnRango / evaluacionesTotales) * 100
          : 100.0;
      _isLoading = false;
    });
  }

  void _mostrarFiltroFechas() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Padding(
                padding: EdgeInsets.all(16.0),
                child: Text('Filtrar Histórico', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              ),
              ListTile(
                leading: const Icon(Icons.history_toggle_off),
                title: const Text('Últimos 3 días'),
                onTap: () => _aplicarFiltro(3, 'Resumen: Últimos 3 días'),
              ),
              ListTile(
                leading: const Icon(Icons.calendar_view_week),
                title: const Text('Última semana'),
                onTap: () => _aplicarFiltro(7, 'Resumen Semanal'),
              ),
              ListTile(
                leading: const Icon(Icons.calendar_month),
                title: const Text('Último mes'),
                onTap: () => _aplicarFiltro(30, 'Resumen Mensual'),
              ),
            ],
          ),
        );
      },
    );
  }

  void _aplicarFiltro(int dias, String titulo) {
    setState(() {
      _diasSeleccionados = dias;
      _tituloPeriodo = titulo;
    });
    Navigator.pop(context);
    _cargarEstadisticas();
  }

  @override
  Widget build(BuildContext context) {
    final nombrePlanta = _cultivoSeleccionado?['tipo_planta'] ?? 'tu cultivo';

    // Semáforo de salud según estabilidad real
    Color colorSalud = Colors.green;
    IconData iconoSalud = Icons.eco;
    String tituloSalud = 'Salud Óptima';

    if (_totalMediciones == 0) {
      colorSalud = Colors.grey;
      iconoSalud = Icons.hourglass_empty;
      tituloSalud = 'Sin Datos';
    } else if (_porcentajeEstabilidad < 50) {
      colorSalud = Colors.red;
      iconoSalud = Icons.warning_amber_rounded;
      tituloSalud = 'Estado Crítico';
    } else if (_porcentajeEstabilidad < 80) {
      colorSalud = Colors.orange;
      iconoSalud = Icons.info_outline;
      tituloSalud = 'Atención Requerida';
    }

    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('Análisis Agronómico', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF1976D2),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.calendar_month, color: Colors.white),
            onPressed: _mostrarFiltroFechas,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Selector de plantaciones
            if (_cultivos.isNotEmpty) ...[
              const Text(
                'Seleccionar Plantación',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF004D40)),
              ),
              const SizedBox(height: 8),
              SizedBox(
                height: 44,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: _cultivos.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (context, index) {
                    final cultivo = _cultivos[index];
                    final seleccionado = _cultivoSeleccionado?['id'] == cultivo['id'];
                    return ChoiceChip(
                      label: Text(cultivo['tipo_planta']),
                      selected: seleccionado,
                      selectedColor: const Color(0xFF1976D2),
                      labelStyle: TextStyle(
                        color: seleccionado ? Colors.white : const Color(0xFF004D40),
                        fontWeight: FontWeight.bold,
                      ),
                      onSelected: (activo) {
                        if (activo && !seleccionado) {
                          setState(() => _cultivoSeleccionado = cultivo);
                          _cargarEstadisticas();
                        }
                      },
                    );
                  },
                ),
              ),
              const SizedBox(height: 20),
            ],

            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(_tituloPeriodo, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF004D40))),
                if (!_isLoading)
                  Text('$_totalMediciones lecturas', style: const TextStyle(color: Colors.grey, fontSize: 13)),
              ],
            ),
            const SizedBox(height: 16),

            if (_isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(vertical: 48),
                  child: CircularProgressIndicator(),
                ),
              )
            else ...[
              Row(
                children: [
                  Expanded(
                    child: _buildStatCard(
                      'Temp. Promedio',
                      _tempProm != null ? '${_tempProm!.toStringAsFixed(1)}°C' : '--',
                      Icons.thermostat,
                      Colors.orange,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildStatCard(
                      'Agua Promedio',
                      _aguaProm != null ? '${_aguaProm!.toStringAsFixed(1)}%' : '--',
                      Icons.water_drop,
                      Colors.blue,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _buildStatCard(
                      'pH Promedio',
                      _phProm != null ? _phProm!.toStringAsFixed(2) : '--',
                      Icons.science,
                      Colors.purple,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildStatCard(
                      'Nutriente A',
                      _nutAProm != null ? '${_nutAProm!.toStringAsFixed(2)} ml/L' : '--',
                      Icons.opacity,
                      Colors.teal,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              _buildStatCard(
                'Nutriente B Promedio',
                _nutBProm != null ? '${_nutBProm!.toStringAsFixed(2)} ml/L' : '--',
                Icons.bubble_chart,
                Colors.deepPurple,
              ),
              const SizedBox(height: 24),

              const Text('Estabilidad del Sistema', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF004D40))),
              const SizedBox(height: 16),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 10)],
                ),
                child: Column(
                  children: [
                    Icon(iconoSalud, size: 60, color: colorSalud),
                    const SizedBox(height: 12),
                    Text(tituloSalud, style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: colorSalud)),
                    const SizedBox(height: 8),
                    Text(
                      _totalMediciones == 0
                          ? 'No hay mediciones registradas para $nombrePlanta en los últimos $_diasSeleccionados días.'
                          : 'Tu cultivo de $nombrePlanta se ha mantenido dentro de sus umbrales ideales el ${_porcentajeEstabilidad.toStringAsFixed(0)}% del tiempo en los últimos $_diasSeleccionados días.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 10)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 12),
          Text(title, style: const TextStyle(color: Colors.grey, fontSize: 13)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 20)),
        ],
      ),
    );
  }
}