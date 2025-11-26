#!/bin/bash

# Script de inicialização rápida do servidor e clientes

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     TRABALHO TCP - CLIENTE/SERVIDOR MULTITHREAD            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Escolha uma opção:"
echo ""
echo "  1) Iniciar SERVIDOR"
echo "  2) Iniciar CLIENTE"
echo "  3) Rodar TESTE AUTOMÁTICO (requer servidor rodando)"
echo "  4) Verificar arquivos disponíveis no servidor"
echo "  5) Limpar downloads do cliente"
echo "  6) Sair"
echo ""
read -p "Opção: " option

case $option in
    1)
        echo ""
        echo "Iniciando servidor na porta 5555..."
        python3 server.py
        ;;
    2)
        echo ""
        read -p "IP do servidor [localhost]: " host
        host=${host:-localhost}
        read -p "Porta [5555]: " port
        port=${port:-5555}
        python3 client.py $host $port
        ;;
    3)
        echo ""
        echo "Certifique-se que o servidor está rodando!"
        read -p "Pressione ENTER para continuar..."
        python3 test_demo.py
        ;;
    4)
        echo ""
        echo "Arquivos disponíveis no servidor:"
        echo "=================================="
        ls -lh server_files/
        echo ""
        echo "Pressione ENTER para continuar..."
        read
        ;;
    5)
        echo ""
        read -p "Confirmar limpeza de client_downloads/? [s/N]: " confirm
        if [ "$confirm" = "s" ] || [ "$confirm" = "S" ]; then
            rm -rf client_downloads/*
            echo "Downloads limpos!"
        else
            echo "Operação cancelada."
        fi
        ;;
    6)
        echo "Saindo..."
        exit 0
        ;;
    *)
        echo "Opção inválida!"
        exit 1
        ;;
esac
