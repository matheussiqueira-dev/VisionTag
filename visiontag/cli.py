from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import cv2

from .config import VisionTagConfig, setup_logging
from .detector import VisionTagger

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}
_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="VisionTag -- deteccao de objetos em tempo real com tags em portugues",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--source", metavar="PATH", help="Caminho para imagem ou video")
    source_group.add_argument("--webcam", type=int, metavar="IDX", help="Indice da webcam (ex: 0)")

    parser.add_argument("--model", default="yolov8n.pt", help="Caminho ou nome do modelo YOLOv8")
    parser.add_argument("--conf", type=float, default=0.7, help="Confianca minima (0-1)")
    parser.add_argument("--max-tags", type=int, default=5, help="Numero maximo de tags")
    parser.add_argument("--min-area", type=float, default=0.01, help="Area minima relativa do bbox (0-1)")
    parser.add_argument("--include-person", action="store_true", help="Incluir pessoa nas tags")
    parser.add_argument("--show", action="store_true", help="Exibir janela com preview e bboxes")
    parser.add_argument("--output", metavar="PATH", help="Salvar imagem/video anotado neste caminho")
    parser.add_argument("--stride", type=int, default=1, help="Processar a cada N frames (webcam/video)")
    parser.add_argument("--print-every", action="store_true", help="Emitir JSON mesmo sem mudanca de tags")
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nivel de log",
    )

    return parser.parse_args()


def emit(tags: list) -> None:
    print(json.dumps({"tags": tags}, ensure_ascii=False), flush=True)


def draw_detections(frame, detections) -> None:
    for label, conf, xyxy in detections:
        x1, y1, x2, y2 = (int(v) for v in xyxy)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
        text = "{} {:.2f}".format(label, conf)
        cv2.putText(
            frame, text, (x1, max(0, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2, cv2.LINE_AA,
        )


def _make_video_writer(output_path, cap):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return cv2.VideoWriter(output_path, fourcc, fps, (width, height))


def run_image(tagger, path, output) -> int:
    image = cv2.imread(path)
    if image is None:
        logger.error("Imagem nao encontrada ou invalida: %s", path)
        print("Erro: imagem nao encontrada ou invalida", file=sys.stderr)
        return 1

    detections = tagger.detect_objects(image)
    tags = [label for label, _, _ in detections]
    emit(tags)

    if output:
        annotated = image.copy()
        draw_detections(annotated, detections)
        if not cv2.imwrite(output, annotated):
            logger.warning("Nao foi possivel salvar imagem anotada em: %s", output)
        else:
            logger.info("Imagem anotada salva em: %s", output)

    return 0


def _process_capture(tagger, cap, show, stride, print_every, writer, window_name) -> int:
    frame_idx = 0
    last_tags = None
    last_detections = []

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_idx % max(1, stride) == 0:
            try:
                detections = tagger.detect_objects(frame)
            except Exception:
                logger.exception("Erro ao processar frame %d", frame_idx)
                detections = []

            last_detections = detections
            tags = [label for label, _, _ in detections]

            if print_every or tags != last_tags:
                emit(tags)
                last_tags = tags

        view = frame.copy()
        draw_detections(view, last_detections)

        if writer:
            writer.write(view)

        if show:
            cv2.imshow(window_name, view)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        frame_idx += 1

    return 0


def run_video(tagger, path, show, stride, output, print_every) -> int:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        logger.error("Nao foi possivel abrir o video: %s", path)
        print("Erro: video nao disponivel", file=sys.stderr)
        return 1

    writer = _make_video_writer(output, cap) if output else None
    try:
        return _process_capture(tagger, cap, show, stride, print_every, writer, "VisionTag - Video")
    finally:
        cap.release()
        if writer:
            writer.release()
            logger.info("Video anotado salvo em: %s", output)
        if show:
            cv2.destroyAllWindows()


def run_webcam(tagger, device, show, stride, output, print_every) -> int:
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        logger.error("Webcam indisponivel: indice %d", device)
        print("Erro: webcam nao disponivel", file=sys.stderr)
        return 1

    writer = _make_video_writer(output, cap) if output else None
    try:
        return _process_capture(tagger, cap, show, stride, print_every, writer, "VisionTag - Webcam")
    finally:
        cap.release()
        if writer:
            writer.release()
            logger.info("Video da webcam salvo em: %s", output)
        if show:
            cv2.destroyAllWindows()


def main() -> int:
    args = parse_args()
    setup_logging(args.log_level)

    config = VisionTagConfig(
        model_path=args.model,
        conf=args.conf,
        max_tags=args.max_tags,
        min_area_ratio=args.min_area,
        include_person=args.include_person,
    )

    try:
        tagger = VisionTagger(config=config)
    except RuntimeError as exc:
        print("Erro ao inicializar o detector: {}".format(exc), file=sys.stderr)
        return 1

    if args.source:
        ext = Path(args.source).suffix.lower()
        if ext in _VIDEO_EXTENSIONS:
            return run_video(tagger, args.source, args.show, args.stride, args.output, args.print_every)
        return run_image(tagger, args.source, args.output)

    return run_webcam(tagger, args.webcam, args.show, args.stride, args.output, args.print_every)


if __name__ == "__main__":
    raise SystemExit(main())
