from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Dict, Iterable, List

import cv2

from .detector import Detection, DetectionOptions, VisionTagger
from .utils import tag_frequency

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VisionTag - deteccao de objetos com tags em portugues")

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--source", help="Caminho de imagem")
    source_group.add_argument("--source-dir", help="Diretorio com imagens")
    source_group.add_argument("--webcam", type=int, help="Indice da webcam (ex.: 0)")

    parser.add_argument("--model", default="yolov8n.pt", help="Modelo YOLO")
    parser.add_argument("--conf", type=float, default=0.7, help="Confianca minima (0-1)")
    parser.add_argument("--max-tags", type=int, default=5, help="Maximo de tags")
    parser.add_argument("--min-area", type=float, default=0.01, help="Area minima relativa do bbox (0-1)")
    parser.add_argument("--include-person", action="store_true", help="Inclui pessoa nas tags")
    parser.add_argument("--max-dimension", type=int, default=1280, help="Reduz imagens grandes para melhorar desempenho")

    parser.add_argument("--details", action="store_true", help="Inclui deteccoes com bbox e confianca")
    parser.add_argument("--save-json", help="Salva resultado completo em arquivo JSON")

    parser.add_argument("--show", action="store_true", help="Exibe janela ao usar webcam")
    parser.add_argument("--stride", type=int, default=1, help="Processa 1 a cada N frames na webcam")
    parser.add_argument("--print-every", action="store_true", help="Imprime tags mesmo sem mudanca")

    return parser.parse_args()


def make_options(args: argparse.Namespace) -> DetectionOptions:
    return DetectionOptions(
        conf=args.conf,
        max_tags=args.max_tags,
        min_area_ratio=args.min_area,
        include_person=args.include_person,
    ).normalized()


def detection_to_dict(item: Detection) -> Dict[str, object]:
    x1, y1, x2, y2 = item.bbox
    return {
        "label": item.label,
        "confidence": round(item.confidence, 4),
        "bbox": {
            "x1": round(x1, 2),
            "y1": round(y1, 2),
            "x2": round(x2, 2),
            "y2": round(y2, 2),
        },
    }


def emit(payload: Dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def maybe_save_json(path: str | None, payload: Dict[str, object]) -> None:
    if not path:
        return
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def image_files_from_directory(directory: Path) -> List[Path]:
    return sorted(
        [
            file
            for file in directory.rglob("*")
            if file.is_file() and file.suffix.lower() in SUPPORTED_SUFFIXES
        ]
    )


def run_image(tagger: VisionTagger, options: DetectionOptions, path: str, details: bool) -> tuple[int, Dict[str, object] | None]:
    image = cv2.imread(path)
    if image is None:
        print("Erro: imagem nao encontrada ou invalida.", file=sys.stderr)
        return 1, None

    summary = tagger.detect_detailed(image, options)
    payload: Dict[str, object] = {
        "source": path,
        "tags": summary.tags,
        "total_detections": len(summary.detections),
        "inference_ms": round(summary.inference_ms, 2),
    }
    if details:
        payload["detections"] = [detection_to_dict(item) for item in summary.detections]

    emit(payload)
    return 0, payload


def run_directory(
    tagger: VisionTagger,
    options: DetectionOptions,
    directory_path: str,
    details: bool,
) -> tuple[int, Dict[str, object] | None]:
    directory = Path(directory_path)
    if not directory.exists() or not directory.is_dir():
        print("Erro: diretorio invalido.", file=sys.stderr)
        return 1, None

    files = image_files_from_directory(directory)
    if not files:
        print("Erro: nenhum arquivo de imagem encontrado no diretorio.", file=sys.stderr)
        return 1, None

    started = perf_counter()
    results: List[Dict[str, object]] = []
    all_tags: List[str] = []

    for file in files:
        image = cv2.imread(str(file))
        if image is None:
            results.append({"file": str(file), "error": "imagem invalida"})
            continue

        summary = tagger.detect_detailed(image, options)
        item: Dict[str, object] = {
            "file": str(file),
            "tags": summary.tags,
            "total_detections": len(summary.detections),
            "inference_ms": round(summary.inference_ms, 2),
        }
        if details:
            item["detections"] = [detection_to_dict(detection) for detection in summary.detections]

        all_tags.extend(summary.tags)
        results.append(item)

    payload = {
        "source_dir": str(directory),
        "total_files": len(files),
        "processed_in_ms": round((perf_counter() - started) * 1000, 2),
        "summary": {
            "tag_frequency": tag_frequency(all_tags),
            "unique_tags": len(set(all_tags)),
        },
        "items": results,
    }

    emit(payload)
    return 0, payload


def draw_detections(frame, detections: Iterable[Detection]) -> None:
    for item in detections:
        x1, y1, x2, y2 = [int(v) for v in item.bbox]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (36, 201, 108), 2)
        label = f"{item.label} {item.confidence:.2f}"
        text_y = max(18, y1 - 8)
        cv2.putText(
            frame,
            label,
            (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (36, 201, 108),
            2,
            cv2.LINE_AA,
        )


def run_webcam(
    tagger: VisionTagger,
    options: DetectionOptions,
    device: int,
    show: bool,
    stride: int,
    print_every: bool,
) -> int:
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        print("Erro: webcam nao disponivel.", file=sys.stderr)
        return 1

    frame_index = 0
    last_tags: List[str] | None = None
    last_detections: List[Detection] = []
    fps_started = perf_counter()
    frames_counter = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_index % max(1, stride) == 0:
                summary = tagger.detect_detailed(frame, options)
                last_detections = summary.detections
                if print_every or summary.tags != last_tags:
                    emit(
                        {
                            "source": "webcam",
                            "tags": summary.tags,
                            "total_detections": len(summary.detections),
                            "inference_ms": round(summary.inference_ms, 2),
                        }
                    )
                    last_tags = summary.tags

            if show:
                view = frame.copy()
                draw_detections(view, last_detections)

                frames_counter += 1
                elapsed = max(0.001, perf_counter() - fps_started)
                fps = frames_counter / elapsed
                cv2.putText(
                    view,
                    f"FPS: {fps:.1f}",
                    (16, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

                cv2.imshow("VisionTag", view)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            frame_index += 1
    finally:
        cap.release()
        if show:
            cv2.destroyAllWindows()

    return 0


def main() -> int:
    args = parse_args()
    options = make_options(args)
    tagger = VisionTagger(model_path=args.model, max_dimension=max(128, args.max_dimension))

    if args.source:
        code, payload = run_image(tagger, options, args.source, args.details)
        if payload:
            maybe_save_json(args.save_json, payload)
        return code

    if args.source_dir:
        code, payload = run_directory(tagger, options, args.source_dir, args.details)
        if payload:
            maybe_save_json(args.save_json, payload)
        return code

    return run_webcam(
        tagger=tagger,
        options=options,
        device=args.webcam,
        show=args.show,
        stride=args.stride,
        print_every=args.print_every,
    )


if __name__ == "__main__":
    raise SystemExit(main())
