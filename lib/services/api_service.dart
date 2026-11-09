
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  final String baseUrl = 'https://aquaplants.onrender.com/api';

  // Obtener token JWT
  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('jwt_token');
  }

  // INICIAR SESIÓN
  Future<bool> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/token/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': email,
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access'];

        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('jwt_token', token);

        return true;
      }

      return false;
    } catch (e) {
      print('Error de conexión: $e');
      return false;
    }
  }

  // OBTENER MEDICIONES
  Future<List<dynamic>> getMediciones({int? dias}) async {
    try {
      final token = await _getToken();

      if (token == null) return [];

      String url = '$baseUrl/mediciones/';

      if (dias != null) {
        url += '?dias=$dias';
      }

      final response = await http.get(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }

      print('Error del servidor: ${response.statusCode}');
      return [];
    } catch (e) {
      print('Error de red: $e');
      return [];
    }
  }

  // CERRAR SESIÓN
  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('jwt_token');
  }

  // OBTENER CONFIGURACIÓN DEL CULTIVO (CU2)
  Future<Map<String, dynamic>?> obtenerConfiguracion() async {
    try {
      final token = await _getToken();

      if (token == null) return null;

      final response = await http.get(
        Uri.parse('$baseUrl/configuracion/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }

      print('Error al obtener configuración: ${response.statusCode}');
      print('Respuesta: ${response.body}');
      return null;
    } catch (e) {
      print('Error al obtener configuración: $e');
      return null;
    }
  }

  // GUARDAR CONFIGURACIÓN DEL CULTIVO (CU2)
  Future<bool> guardarConfiguracion(
    String tipoPlanta,
    String tempMin,
    String tempMax,
    String phMin,
    String phMax,
    String aguaMin,
    String aguaMax,
  ) async {
    try {
      final token = await _getToken();

      if (token == null) return false;

      final response = await http.post(
        Uri.parse('$baseUrl/configuracion/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({
          'tipo_planta': tipoPlanta,
          'temp_min': double.parse(tempMin),
          'temp_max': double.parse(tempMax),
          'ph_min': double.parse(phMin),
          'ph_max': double.parse(phMax),
          'agua_min': double.parse(aguaMin),
          'agua_max': double.parse(aguaMax),
        }),
      );

      if (response.statusCode == 200) {
        return true;
      }

      print('Error del servidor: ${response.statusCode}');
      print('Respuesta: ${response.body}');
      return false;
    } catch (e) {
      print('Error al guardar configuración: $e');
      return false;
    }
  }

  // OBTENER ALERTAS
  Future<List<dynamic>> getAlertas() async {
    try {
      final token = await _getToken();

      if (token == null) return [];

      final response = await http.get(
        Uri.parse('$baseUrl/alertas/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }

      return [];
    } catch (e) {
      print('Error al obtener alertas: $e');
      return [];
    }
  }

  // RESOLVER ALERTA
  Future<bool> resolverAlerta(int id) async {
    try {
      final token = await _getToken();

      if (token == null) return false;

      final response = await http.post(
        Uri.parse('$baseUrl/alertas/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({'id': id}),
      );

      return response.statusCode == 200;
    } catch (e) {
      print('Error al resolver alerta: $e');
      return false;
    }
  }
}
