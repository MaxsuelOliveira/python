#!/usr/bin/env python3
"""Backup Tool unificado

Combina funcionalidades dos projetos `backup_aws` e `backup_nuvem`:
- copia conteúdo de uma pasta origem para pasta temporária
- compacta em ZIP com timestamp
- opção --dry-run (simular)
- opção --remove (apagar origem após backup)
- opção --upload-s3 (stub, requer boto3 e credenciais)

Uso básico:
    python main.py --source ./meus_arquivos --target ./temp --zip-dir ./backup

"""
import os
import shutil
import zipfile
from datetime import datetime
import argparse
import sys


def zipar_pasta(pasta_origem, pasta_destino, nome_zip, dry_run=False):
    if not os.path.exists(pasta_origem):
        raise FileNotFoundError(pasta_origem)

    if not os.path.exists(pasta_destino) and not dry_run:
        os.makedirs(pasta_destino, exist_ok=True)

    agora = datetime.now()
    nome_zip_com_data = f"{nome_zip}-{agora.strftime('%Y%m%d%H%M%S')}.zip"
    destino_zip = os.path.join(pasta_destino, nome_zip_com_data)

    if dry_run:
        print(f"[dry-run] Criaria zip: {destino_zip}")
        for pasta_raiz, _, arquivos in os.walk(pasta_origem):
            for arquivo in arquivos:
                caminho_completo = os.path.join(pasta_raiz, arquivo)
                print(f"[dry-run] Incluir: {os.path.relpath(caminho_completo, pasta_origem)}")
        return destino_zip

    with zipfile.ZipFile(destino_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for pasta_raiz, _, arquivos in os.walk(pasta_origem):
            for arquivo in arquivos:
                caminho_completo = os.path.join(pasta_raiz, arquivo)
                arcname = os.path.relpath(caminho_completo, os.path.dirname(pasta_origem))
                zipf.write(caminho_completo, arcname)

    print("Compactado com sucesso:", destino_zip)
    return destino_zip


def copiar_para_temp(source, target, exclude=None, dry_run=False):
    if not os.path.exists(source):
        raise FileNotFoundError(source)
    os.makedirs(target, exist_ok=True)

    for item in os.listdir(source):
        if exclude and item in exclude:
            continue
        s = os.path.join(source, item)
        d = os.path.join(target, item)
        if os.path.isdir(s):
            if dry_run:
                print(f"[dry-run] copytree {s} -> {d}")
            else:
                shutil.copytree(s, d, copy_function=shutil.copy2)
        else:
            if dry_run:
                print(f"[dry-run] copy {s} -> {d}")
            else:
                shutil.copy2(s, d)


def remover_origem(path, dry_run=False):
    if dry_run:
        print(f"[dry-run] remover origem: {path}")
        return
    shutil.rmtree(path)
    print("Origem removida:", path)


def upload_s3_stub(zip_path, bucket_name):
    # stub: implement if user wants S3 upload (requires boto3 and creds)
    print(f"Upload stub: enviaria {zip_path} para s3://{bucket_name}/")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description='Backup Tool unificado')
    parser.add_argument('--source', '-s', default='./', help='pasta de origem')
    parser.add_argument('--target', '-t', default='./temp', help='pasta temporaria para copia')
    parser.add_argument('--zip-dir', '-z', default='./backup', help='pasta onde salvar zips')
    parser.add_argument('--zip-name', default='backup', help='prefixo do arquivo zip')
    parser.add_argument('--exclude', help='pastas a excluir, separadas por vírgula')
    parser.add_argument('--dry-run', action='store_true', help='simular as ações sem modificar')
    parser.add_argument('--remove', action='store_true', help='remover a origem após backup (use com cuidado)')
    parser.add_argument('--upload-s3', nargs='?', const='my-bucket', help='(opcional) enviar zip para S3 (requiere boto3)')
    # compression options (from compressing_files)
    parser.add_argument('--compress', help='compactar uma pasta com o compressor avançado (path)')
    parser.add_argument('--compress-gui', action='store_true', help='abrir GUI de compactação (tkinter)')
    parser.add_argument('--compress-format', choices=['xz', 'gz', 'zip'], default='xz', help='formato para compressão')
    parser.add_argument('--compress-level', type=int, default=9, help='nível de compressão 0-9')

    args = parser.parse_args(argv)

    exclude = args.exclude.split(',') if args.exclude else None

    try:
        # compress GUI
        if args.compress_gui:
            try:
                from backup_tool.compress.gui import App
                import tkinter as tk
                root = tk.Tk()
                app = App(root)
                root.mainloop()
                return
            except Exception as e:
                print('Falha ao iniciar GUI:', e)
                return

        # compress folder via advanced compressor
        if args.compress:
            try:
                from backup_tool.compress.functions import create_archive_parallel
                out = create_archive_parallel(args.compress, fmt=args.compress_format, compress_level=args.compress_level)
                print('Compactado com sucesso:', out)
                return
            except Exception as e:
                print('Erro na compactação:', e)
                sys.exit(2)

        copiar_para_temp(args.source, args.target, exclude=exclude, dry_run=args.dry_run)
        zip_path = zipar_pasta(args.target, args.zip_dir, args.zip_name, dry_run=args.dry_run)

        if args.upload_s3:
            upload_s3_stub(zip_path, args.upload_s3)

        if args.remove and not args.dry_run:
            remover_origem(args.source, dry_run=args.dry_run)

        print('Operação finalizada')

    except Exception as e:
        print('Erro:', e)
        sys.exit(2)


if __name__ == '__main__':
    main()
