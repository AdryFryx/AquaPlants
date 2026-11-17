import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AnaliticaScreen extends StatefulWidget {
  const AnaliticaScreen({super.key});

  @override
  State<AnaliticaScreen> createState() => _AnaliticaScreenState();
}

class _AnaliticaScreenState extends State<AnaliticaScreen> {
  String _tituloPeriodo = 'Resumen Semanal';
  bool _isLoading = true;

  // Variables dinámicas para los promedios
  String _promedioTemp = '--';
  String _promedioAgua = '--';
  String _promedioPh = '--';
  String _promedioNutA = '--';
  String _promedioNutB = '--';

  @override
  void initState() {
    super.initState();
    _cargarAnaliticas(7); // Carga inicial de 7 días
  }

  Future<void> _cargarAnaliticas(int dias) async {
    setState(() => _isLoading = true);
    
    final datos = await ApiService().getMediciones(dias: dias);
    
    if (datos.isNotEmpty && mounted) {
      double sumTemp = 0, sumAgua = 0, sumPh = 0, sumNutA = 0, sumNutB = 0;
      
      for (var m in datos) {
        sumTemp += (m['temperatura'] as num?)?.toDouble() ?? 0.0;
        sumAgua += (m['nivel_agua'] as num?)?.toDouble() ?? 0.0;
        sumPh += (m['ph'] as num?)?.toDouble() ?? 0.0;
        sumNutA += (m['nutriente_a'] as num?)?.toDouble() ?? 0.0;
        sumNutB += (m['nutriente_b'] as num?)?.toDouble() ?? 0.0;
      }

      int total = datos.length;

      setState(() {
        _promedioTemp = '${(sumTemp / total).toStringAsFixed(1)}°C';
        _promedioAgua = '${(sumAgua / total).toStringAsFixed(1)}%';
        _promedioPh = (sumPh / total).toStringAsFixed(1);
        _promedioNutA = '${(sumNutA / total).toStringAsFixed(1)} ml/L';
        _promedioNutB = '${(sumNutB / total).toStringAsFixed(1)} ml/L';
        _isLoading = false;
      });
    } else if (mounted) {
      setState(() {
        _promedioTemp = '--'; _promedioAgua = '--'; _promedioPh = '--';
        _promedioNutA = '--'; _promedioNutB = '--';
        _isLoading = false;
      });
    }
  }

  void _mostrarFiltroFechas() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
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
                onTap: () { Navigator.pop(context); _aplicarFiltro(3, 'Resumen: Últimos 3 días'); },
              ),
              ListTile(
                leading: const Icon(Icons.calendar_view_week),
                title: const Text('Última semana'),
                onTap: () { Navigator.pop(context); _aplicarFiltro(7, 'Resumen Semanal'); },
              ),
            ],
          ),
        );
      },
    );
  }

  void _aplicarFiltro(int dias, String titulo) {
    setState(() {
      _tituloPeriodo = titulo;
    });
    _cargarAnaliticas(dias);
  }

  @override
  Widget build(BuildContext context) {
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
          )
        ],
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_tituloPeriodo, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF004D40))),
                const SizedBox(height: 16),
                
                // Fila 1
                Row(
                  children: [
                    Expanded(child: _buildStatCard('Temp. Promedio', _promedioTemp, Icons.thermostat, Colors.orange)),
                    const SizedBox(width: 12),
                    Expanded(child: _buildStatCard('Agua Promedio', _promedioAgua, Icons.water_drop, Colors.blue)),
                  ],
                ),
                const SizedBox(height: 12),
                
                // Fila 2
                Row(
                  children: [
                    Expanded(child: _buildStatCard('pH Promedio', _promedioPh, Icons.science, Colors.purple)),
                    const SizedBox(width: 12),
                    Expanded(child: _buildStatCard('Nutriente A (Prom)', _promedioNutA, Icons.opacity, Colors.teal)),
                  ],
                ),
                const SizedBox(height: 12),
                
                // Fila 3
                Row(
                  children: [
                    Expanded(child: _buildStatCard('Nutriente B (Prom)', _promedioNutB, Icons.bubble_chart, Colors.deepPurple)),
                    const SizedBox(width: 12),
                    Expanded(child: Container()), // Espacio vacío para balancear
                  ],
                ),
              ],
            ),
          ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Container(
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