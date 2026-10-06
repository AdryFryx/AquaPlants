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
  
  // Variables en blanco para iniciar
  String tempActual = '--';
  String aguaActual = '--';
  String phActual = '--';
  List<FlSpot> historialAgua = [];

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
    _timer?.cancel(); // Apagamos el temporizador al salir de la pantalla
    super.dispose();
  }

  Future<void> _cargarDatos() async {
    final datos = await _apiService.getMediciones();
    
    if (datos.isNotEmpty && mounted) {
      // Tomamos la última medición (la más reciente suele ser la última de la lista)
      final ultima = datos.last;
      
      // Tomamos los últimos 7 registros para el gráfico de nivel de agua
      final ultimos7 = datos.length > 7 ? datos.sublist(datos.length - 7) : datos;
      List<FlSpot> spotsTemporales = [];
      
      for (int i = 0; i < ultimos7.length; i++) {
        spotsTemporales.add(FlSpot(i.toDouble(), (ultimos7[i]['nivel_agua'] as num).toDouble()));
      }

      setState(() {
        tempActual = '${ultima['temperatura']}°C';
        aguaActual = '${ultima['nivel_agua']}%';
        phActual = '${ultima['ph']}';
        historialAgua = spotsTemporales;
      });
    }
  }

  // Lógica simple de umbrales para los colores (Semáforo)
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
        title: const Text('Mi Cultivo - Torre 1', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF00BFA5),
        elevation: 0,
        actions: [ ],
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
            const SizedBox(height: 32),
            const Text(
              'Histórico de Consumo Hídrico',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF004D40)),
            ),
            const SizedBox(height: 16),
            Container(
              height: 300,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10)],
              ),
              child: historialAgua.isEmpty
                  ? const Center(child: CircularProgressIndicator())
                  : LineChart(
                      LineChartData(
                        gridData: const FlGridData(show: true, drawVerticalLine: false),
                        titlesData: const FlTitlesData(
                          rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                          topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        ),
                        borderData: FlBorderData(show: false),
                        lineBarsData: [
                          LineChartBarData(
                            spots: historialAgua,
                            isCurved: true,
                            color: const Color(0xFF00BFA5),
                            barWidth: 4,
                            isStrokeCapRound: true,
                            belowBarData: BarAreaData(
                              show: true,
                              color: const Color(0xFF00BFA5).withOpacity(0.2),
                            ),
                          ),
                        ],
                      ),
                    ),
            ),
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
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10)],
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
}