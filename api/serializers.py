
from django.contrib.auth.models import User, Group
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from rest_framework import serializers

from .models import Dispositivo, Medicion


class DispositivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispositivo
        fields = '__all__'


class MedicionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicion
        fields = '__all__'


class RegistroSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    confirmar_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'password',
            'confirmar_password'
        ]

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'Este correo ya está registrado.'
            )

        return value

    def validate(self, attrs):
        password = attrs.get('password')
        confirmar_password = attrs.pop('confirmar_password')

        if password != confirmar_password:
            raise serializers.ValidationError({
                'confirmar_password': 'Las contraseñas no coinciden.'
            })

        usuario = User(
            username=attrs.get('username'),
            email=attrs.get('email'),
            first_name=attrs.get('first_name'),
            last_name=attrs.get('last_name')
        )

        validate_password(password, user=usuario)

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password')

        usuario = User.objects.create_user(
            password=password,
            **validated_data
        )

        grupo, _ = Group.objects.get_or_create(
            name='CLIENTE'
        )

        usuario.groups.add(grupo)

        return usuario
