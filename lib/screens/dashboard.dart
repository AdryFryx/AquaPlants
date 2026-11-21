import 'dart:async';
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/api_service.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final ApiService _apiService = ApiService();
  Timer? _timer;
  bool _isFetching = false;

  // Selector de plantaciones
  List<dynamic> _cultivos = [];
  Map<String, dynamic>? _cultivoSeleccionado;

  // Variables en tiempo real (valores numéricos para evaluar umbrales)
  double? _tempVal;
  double? _aguaVal;
  double? _phVal;
  double? _nutAVal;
  double? _nutBVal;

  // Historiales para los 5 gráficos
  List<FlSpot> historialTemp = [];
  List<FlSpot> historialAgua = [];
  List<FlSpot> historialPh = [];
  List<FlSpot> historialNutA = [];
  List<FlSpot> historialNutB = [];

  final PageController _pageController = PageController();
  int _graficoActual = 0;

  @override
  void initState() {
    super.initState();
    _inicializarDashboard();
    _timer = Timer.periodic(const Duration(seconds: 10), (timer) {
      _cargarDatos();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _inicializarDashboard() async {
    final cultivos = await _apiService.getMisCultivos();
    if (mounted) {
      setState(() {
        _cultivos = cultivos;
        if (_cultivos.isNotEmpty) {
          _cultivoSeleccionado = _cultivos.first;
        }
      });
    }
    await _cargarDatos();
  }

  Future<void> _cargarDatos() async {
    if (_isFetching) return;
    _isFetching = true;

    try {
      final int? dispositivoId = _cultivoSeleccionado?['dispositivo_id'];
      final datos = await _apiService.getMediciones(dispositivoId: dispositivoId);

      if (mounted) {
        if (datos.isEmpty) {
          setState(() {
            _tempVal = _aguaVal = _phVal = _nutAVal = _nutBVal = null;
            historialTemp = [];
            historialAgua = [];
            historialPh = [];
            historialNutA = [];
            historialNutB = [];
          });
          return;
        }

        final ultima = datos.first;
        final ultimos7 = datos.take(7).toList().reversed.toList();

        List<FlSpot> spotsTemp = [];
        List<FlSpot> spotsAgua = [];
        List<FlSpot> spotsPh = [];
        List<FlSpot> spotsNutA = [];
        List<FlSpot> spotsNutB = [];

        for (int i = 0; i < ultimos7.length; i++) {
          spotsTemp.add(FlSpot(i.toDouble(), (ultimos7[i]['temperatura'] as num?)?.toDouble() ?? 0.0));
          spotsAgua.add(FlSpot(i.toDouble(), (ultimos7[i]['nivel_agua'] as num?)?.toDouble() ?? 0.0));
          spotsPh.add(FlSpot(i.toDouble(), (ultimos7[i]['ph'] as num?)?.toDouble() ?? 0.0));
          spotsNutA.add(FlSpot(i.toDouble(), (ultimos7[i]['nutriente_a'] as num?)?.toDouble() ?? 0.0));
          spotsNutB.add(FlSpot(i.toDouble(), (ultimos7[i]['nutriente_b'] as num?)?.toDouble() ?? 0.0));
        }

        setState(() {
          _tempVal = (ultima['temperatura'] as num?)?.toDouble();
          _aguaVal = (ultima['nivel_agua'] as num?)?.toDouble();
          _phVal = (ultima['ph'] as num?)?.toDouble();
          _nutAVal = (ultima['nutriente_a'] as num?)?.toDouble();
          _nutBVal = (ultima['nutriente_b'] as num?)?.toDouble();

          historialTemp = spotsTemp;
          historialAgua = spotsAgua;
          historialPh = spotsPh;
          historialNutA = spotsNutA;
          historialNutB = spotsNutB;
        });
      }
    } catch (e) {
      print("Error silencioso al cargar: $e");
    } finally {
      _isFetching = false;
    }
  }

  /// Evalúa si el valor está dentro del rango ideal de la planta seleccionada
  Color _colorSegunRegla(String variable, double? valor, Color colorPorDefecto) {
    if (valor == null) return Colors.grey;
    final reglas = _cultivoSeleccionado?['reglas'] as Map<String, dynamic>?;
    final regla = reglas?[variable];
    if (regla == null) return colorPorDefecto;

    final min = (regla['minimo'] as num).toDouble();
    final max = (regla['maximo'] as num).toDouble();
    if (valor < min || valor > max) return Colors.red;
    return Colors.green;
  }

  String _rangoTexto(String variable, String unidad) {
    final reglas = _cultivoSeleccionado?['reglas'] as Map<String, dynamic>?;
    final regla = reglas?[variable];
    if (regla == null) return '';
    return '${regla['minimo']}-${regla['maximo']}$unidad';
  }

  @override
  Widget build(BuildContext context) {
    final tituloAppBar = _cultivoSeleccionado != null
        ? '${_cultivoSeleccionado!['tipo_planta']} · ${_cultivoSeleccionado!['dispositivo_nombre']}'
        : 'Mi Cultivo';

    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: Text(
          tituloAppBar,
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
        ),
        backgroundColor: const Color(0xFF00BFA5),
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Menú selector de plantaciones
            if (_cultivos.isNotEmpty) ...[
              const Text(
                'Mis Plantaciones',
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
                      selectedColor: const Color(0xFF00BFA5),
                      labelStyle: TextStyle(
                        color: seleccionado ? Colors.white : const Color(0xFF004D40),
                        fontWeight: FontWeight.bold,
                      ),
                      onSelected: (activo) {
                        if (activo && !seleccionado) {
                          setState(() => _cultivoSeleccionado = cultivo);
                          _cargarDatos();
                        }
                      },
                    );
                  },
                ),
              ),
              const SizedBox(height: 20),
            ],

            const Text(
              'Estado en Tiempo Real',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF004D40)),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildMetricCard(
                    'Temp.',
                    _tempVal != null ? '${_tempVal}°C' : '--',
                    _rangoTexto('TEMP', '°C'),
                    _colorSegunRegla('TEMP', _tempVal, Colors.orange),
                    Icons.thermostat,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildMetricCard(
                    'Agua',
                    _aguaVal != null ? '${_aguaVal}%' : '--',
                    _rangoTexto('AGUA', '%'),
                    _colorSegunRegla('AGUA', _aguaVal, Colors.blue),
                    Icons.water_drop,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildMetricCard(
                    'pH',
                    _phVal != null ? '$_phVal' : '--',
                    _rangoTexto('PH', ''),
                    _colorSegunRegla('PH', _phVal, Colors.purple),
                    Icons.science,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _buildMetricCard(
                    'Nutriente A',
                    _nutAVal != null ? '$_nutAVal ml/L' : '--',
                    _rangoTexto('NUT_A', ''),
                    _colorSegunRegla('NUT_A', _nutAVal, Colors.teal),
                    Icons.opacity,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildMetricCard(
                    'Nutriente B',
                    _nutBVal != null ? '$_nutBVal ml/L' : '--',
                    _rangoTexto('NUT_B', ''),
                    _colorSegunRegla('NUT_B', _nutBVal, Colors.deepPurple),
                    Icons.bubble_chart,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 32),
            const Text(
              'Histórico de Variables (Desliza)',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF004D40)),
            ),
            const SizedBox(height: 16),
            Container(
              height: 320,
              padding: const EdgeInsets.only(top: 16, left: 16, right: 16, bottom: 8),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 10)],
              ),
              child: Column(
                children: [
                  Expanded(
                    child: PageView(
                      controller: _pageController,
                      onPageChanged: (index) {
                        setState(() => _graficoActual = index);
                      },
                      children: [
                        _buildChart('Temperatura (°C)', historialTemp, Colors.orange),
                        _buildChart('Nivel de Agua (%)', historialAgua, Colors.blue),
                        _buildChart('Nivel de pH', historialPh, Colors.purple),
                        _buildChart('Nutriente A (ml/L)', historialNutA, Colors.teal),
                        _buildChart('Nutriente B (ml/L)', historialNutB, Colors.deepPurple),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(5, (index) {
                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        height: 8,
                        width: _graficoActual == index ? 24 : 8,
                        decoration: BoxDecoration(
                          color: _graficoActual == index ? const Color(0xFF00BFA5) : Colors.grey[300],
                          borderRadius: BorderRadius.circular(4),
                        ),
                      );
                    }),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricCard(String title, String value, String rango, Color statusColor, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 10)],
        border: Border(bottom: BorderSide(color: statusColor, width: 4)),
      ),
      child: Column(
        children: [
          Icon(icon, color: statusColor, size: 28),
          const SizedBox(height: 6),
          Text(title, style: const TextStyle(color: Colors.grey, fontSize: 13)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 20)),
          if (rango.isNotEmpty)
            Text('Ideal: $rango', style: TextStyle(color: Colors.grey[600], fontSize: 11)),
        ],
      ),
    );
  }

  Widget _buildChart(String titulo, List<FlSpot> datos, Color color) {
    if (datos.isEmpty) {
      return const Center(child: Text('Sin mediciones para esta torre', style: TextStyle(color: Colors.grey)));
    }
    return Column(
      children: [
        Text(titulo, style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 16)),
        const SizedBox(height: 16),
        Expanded(
          child: LineChart(
            LineChartData(
              gridData: const FlGridData(show: true, drawVerticalLine: false),
              titlesData: const FlTitlesData(
                rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
              ),
              borderData: FlBorderData(show: false),
              lineBarsData: [
                LineChartBarData(
                  spots: datos,
                  isCurved: true,
                  color: color,
                  barWidth: 4,
                  isStrokeCapRound: true,
                  belowBarData: BarAreaData(show: true, color: color.withValues(alpha: 0.2)),
                ),
              ],
            ),
            duration: Duration.zero,
          ),
        ),
      ],
    );
  }
}