import argparse
import json
import sys

import cv2

from .detector import VisionTagger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VisionTag - tags simples por deteccao")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--source", help="Caminho da imagem")
    source_group.add_argument("--webcam", type=int, help="Indice da webcam (ex: 0)")

    parser.add_argument("--model", default="yolov8n.pt", help="Modelo YOLOv8")
    parser.add_argument("--conf", type=float, default=0.7, help="Confianca minima")
    parser.add_argument("--max-tags", type=int, default=5, help="Maximo de tags")
    parser.add_argument(
        "--min-area",
        type=float,
        default=0.01,
        help="Area minima relativa do bbox (0-1)",
    )
    parser.add_argument(
        "--include-person",
        action="store_true",
        help="Incluir pessoa nas tags",
    )
    parser.add_argument("--show", action="store_true", help="Mostrar janela da webcam")
    parser.add_argument(
        "--stride",
        type=int,
        default=1,
        help="Processa a cada N frames (webcam)",
    )
    parser.add_argument(
        "--print-every",
        action="store_true",
        help="Imprime tags mesmo sem mudanca (webcam)",
    )

    return parser.parse_args()


def emit(tags) -> None:
    print(json.dumps({"tags": tags}, ensure_ascii=False), flush=True)


def unique_labels(detections):
    tags = []
    seen = set()
    for label, _, _ in detections:
        if label in seen:
            continue
        tags.append(label)
        seen.add(label)
    return tags


def draw_detections(frame, detections):
    for label, conf, xyxy in detections:
        x1, y1, x2, y2 = [int(v) for v in xyxy]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
        text = f"{label} {conf:.2f}"
        y_text = max(0, y1 - 8)
        cv2.putText(
            frame,
            text,
            (x1, y_text),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 200, 0),
            2,
            cv2.LINE_AA,
        )


def run_image(tagger: VisionTagger, path: str) -> int:
    image = cv2.imread(path)
    if image is None:
        print("Erro: imagem nao encontrada ou invalida", file=sys.stderr)
        return 1
    tags = tagger.detect(image)
    emit(tags)
    return 0


def run_webcam(tagger: VisionTagger, device: int, show: bool, stride: int, print_every: bool) -> int:
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        print("Erro: webcam nao disponivel", file=sys.stderr)
        return 1

    frame_idx = 0
    last_tags = None
    last_detections = []

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_idx % max(1, stride) == 0:
                detections = tagger.detect_objects(frame)
                last_detections = detections
                tags = unique_labels(detections)
                if print_every or tags != last_tags:
                    emit(tags)
                    last_tags = tags

            if show:
                view = frame.copy()
                draw_detections(view, last_detections)
                cv2.imshow("VisionTag", view)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            frame_idx += 1
    finally:
        cap.release()
        if show:
            cv2.destroyAllWindows()

    return 0


def main() -> int:
    args = parse_args()
    tagger = VisionTagger(
        model_path=args.model,
        conf=args.conf,
        max_tags=args.max_tags,
        min_area_ratio=args.min_area,
        include_person=args.include_person,
    )

    if args.source:
        return run_image(tagger, args.source)
    return run_webcam(tagger, args.webcam, args.show, args.stride, args.print_every)


if __name__ == "__main__":
    raise SystemExit(main())
