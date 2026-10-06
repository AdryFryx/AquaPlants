import 'package:flutter/material.dart';
import 'dashboard.dart';
import 'perfil.dart';
import 'alertas.dart';
import 'analitica.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _indiceActual = 0;

  final List<Widget> _pantallas = [
    const DashboardScreen(),
    const AnaliticaScreen(),
    const AlertasScreen(),
    const PerfilScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pantallas[_indiceActual],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _indiceActual,
        type: BottomNavigationBarType.fixed, // Necesario cuando hay > 3 items
        onTap: (index) {
          setState(() {
            _indiceActual = index;
          });
        },
        selectedItemColor: const Color(0xFF00BFA5),
        unselectedItemColor: Colors.grey,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.grass), label: 'Cultivo'),
          BottomNavigationBarItem(icon: Icon(Icons.insights), label: 'Análisis'),
          BottomNavigationBarItem(icon: Icon(Icons.warning_rounded), label: 'Alertas'),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Perfil'),
        ],
      ),
    );
  }
}