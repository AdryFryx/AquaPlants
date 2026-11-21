
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  final String baseUrl = 'http://127.0.0.1:8000/api'; //nube (https://aquaplants.onrender.com/api) || local(http://127.0.0.1:8000/api)

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
  Future<List<dynamic>> getMediciones({int? dias, int? dispositivoId}) async {
    try {
      final token = await _getToken();
      if (token == null) return [];

      final params = <String, String>{};
      if (dias != null) params['dias'] = dias.toString();
      if (dispositivoId != null) params['dispositivo_id'] = dispositivoId.toString();

      final uri = Uri.parse('$baseUrl/mediciones/').replace(
        queryParameters: params.isNotEmpty ? params : null,
      );

      final response = await http.get(
        uri,
        headers: {'Authorization': 'Bearer $token'},
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return [];
    } catch (e) {
      print('Error al obtener mediciones: $e');
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

  // REPORTAR FALLA (CLIENTE -> ADMIN)
  Future<bool> reportarFalla(String motivo, String detalle) async {
    try {
      final token = await _getToken();
      if (token == null) return false;

      final response = await http.post(
        Uri.parse('$baseUrl/reportar-falla/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: jsonEncode({
          'motivo': motivo,
          'detalle': detalle,
        }),
      );

      return response.statusCode == 201;
    } catch (e) {
      print('Error al reportar falla: $e');
      return false;
    }
  }

  // OBTENER PLANTACIONES ASIGNADAS AL USUARIO
  Future<List<dynamic>> getMisCultivos() async {
    try {
      final token = await _getToken();
      if (token == null) return [];

      final response = await http.get(
        Uri.parse('$baseUrl/mis-cultivos/'),
        headers: {'Authorization': 'Bearer $token'},
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return [];
    } catch (e) {
      print('Error al cargar cultivos: $e');
      return [];
    }
  }
}
