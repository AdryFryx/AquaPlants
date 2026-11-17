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
  
  // Variables en tiempo real
  String tempActual = '--';
  String aguaActual = '--';
  String phActual = '--';
  String nutAActual = '--';
  String nutBActual = '--';
  
  // Historiales para los 5 gráficos
  List<FlSpot> historialTemp = [];
  List<FlSpot> historialAgua = [];
  List<FlSpot> historialPh = [];
  List<FlSpot> historialNutA = [];
  List<FlSpot> historialNutB = [];

  // Controlador del carrusel
  final PageController _pageController = PageController();
  int _graficoActual = 0;

  @override
  void initState() {
    super.initState();
    _cargarDatos(); 
    _timer = Timer.periodic(const Duration(seconds: 5), (timer) {
      _cargarDatos();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _cargarDatos() async {
    if (_isFetching) return; 
    _isFetching = true; 

    try {
      final datos = await _apiService.getMediciones();
      
      if (datos.isNotEmpty && mounted) {
        final ultima = datos.last;
        final ultimos7 = datos.length > 7 ? datos.sublist(datos.length - 7) : datos;
        
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
          tempActual = '${ultima['temperatura']}°C';
          aguaActual = '${ultima['nivel_agua']}%';
          phActual = '${ultima['ph']}';
          nutAActual = '${ultima['nutriente_a'] ?? '0.0'} ml/L';
          nutBActual = '${ultima['nutriente_b'] ?? '0.0'} ml/L';
          
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

  Color _obtenerColorTemp(String temp) {
    if (temp == '--') return Colors.grey;
    double valor = double.parse(temp.replaceAll('°C', ''));
    if (valor > 25.0) return Colors.red;
    if (valor < 21.0) return Colors.amber;
    return Colors.green;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: const Text('Mi Cultivo', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF00BFA5),
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Estado en Tiempo Real',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF004D40)),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(child: _buildMetricCard('Temp.', tempActual, _obtenerColorTemp(tempActual), Icons.thermostat)),
                const SizedBox(width: 12),
                Expanded(child: _buildMetricCard('Agua', aguaActual, Colors.blue, Icons.water_drop)),
                const SizedBox(width: 12),
                Expanded(child: _buildMetricCard('pH', phActual, Colors.purple, Icons.science)),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(child: _buildMetricCard('Nutriente A', nutAActual, Colors.teal, Icons.opacity)),
                const SizedBox(width: 12),
                Expanded(child: _buildMetricCard('Nutriente B', nutBActual, Colors.deepPurple, Icons.bubble_chart)),
              ],
            ),
            
            const SizedBox(height: 32),
            const Text(
              'Histórico de Variables (Desliza)',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF004D40)),
            ),
            const SizedBox(height: 16),
            
            // CARRUSEL DE GRÁFICOS
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
                        setState(() { _graficoActual = index; });
                      },
                      children: [
                        _buildChart('Temperatura (°C)', historialTemp, Colors.orange),
                        _buildChart('Consumo de Agua (%)', historialAgua, Colors.blue),
                        _buildChart('Nivel de pH', historialPh, Colors.purple),
                        _buildChart('Nutriente A (ml/L)', historialNutA, Colors.teal),
                        _buildChart('Nutriente B (ml/L)', historialNutB, Colors.deepPurple),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  // PUNTOS INDICADORES DEL CARRUSEL
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

  Widget _buildMetricCard(String title, String value, Color statusColor, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 10)],
        border: Border(bottom: BorderSide(color: statusColor, width: 4)),
      ),
      child: Column(
        children: [
          Icon(icon, color: statusColor, size: 32),
          const SizedBox(height: 8),
          Text(title, style: const TextStyle(color: Colors.grey, fontSize: 14)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 22)),
        ],
      ),
    );
  }

  Widget _buildChart(String titulo, List<FlSpot> datos, Color color) {
    if (datos.isEmpty) {
      return const Center(child: CircularProgressIndicator());
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
          ),
        ),
      ],
    );
  }
}