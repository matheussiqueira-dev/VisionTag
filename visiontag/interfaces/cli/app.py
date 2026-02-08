from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

from ...core.exceptions import InputValidationError
from ...core.models import Detection, DetectionRequest
from ...infrastructure.image_io import is_supported_image_file, load_image_file
from ...infrastructure.yolo_detector import YoloObjectDetector
from ...labels_pt import COCO_PT
from ...services.tagging import TaggingService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="VisionTag - deteccao de objetos com tags em portugues"
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--source", help="Arquivo de imagem ou diretorio com imagens")
    source_group.add_argument("--webcam", type=int, help="Indice da webcam (ex: 0)")

    parser.add_argument("--model", default="yolov8n.pt", help="Modelo YOLOv8")
    parser.add_argument("--conf", type=float, default=0.7, help="Confianca minima (0-1)")
    parser.add_argument("--max-tags", type=int, default=5, help="Maximo de tags (1-50)")
    parser.add_argument(
        "--min-area",
        type=float,
        default=0.01,
        help="Area minima relativa do bbox (0-1)",
    )
    parser.add_argument(
        "--include-person",
        action="store_true",
        help="Inclui pessoa nas tags",
    )
    parser.add_argument(
        "--include-details",
        action="store_true",
        help="Inclui bbox e confianca no resultado JSON",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Processa diretorios de forma recursiva",
    )
    parser.add_argument("--show", action="store_true", help="Exibe janela da webcam")
    parser.add_argument(
        "--stride",
        type=int,
        default=1,
        help="Processa a cada N frames (webcam)",
    )
    parser.add_argument(
        "--print-every",
        action="store_true",
        help="Imprime tags mesmo sem mudanca no stream da webcam",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Formata JSON com indentacao",
    )
    return parser.parse_args()


def _emit(payload: dict, pretty: bool) -> None:
    indent = 2 if pretty else None
    print(json.dumps(payload, ensure_ascii=False, indent=indent), flush=True)


def _format_detections(detections: list[Detection]) -> list[dict]:
    return [
        {
            "label": item.label,
            "confidence": round(item.confidence, 4),
            "bbox": [round(value, 2) for value in item.bbox],
        }
        for item in detections
    ]


def _iter_image_files(directory: Path, recursive: bool) -> list[Path]:
    if recursive:
        items = [path for path in directory.rglob("*") if path.is_file()]
    else:
        items = [path for path in directory.iterdir() if path.is_file()]
    return sorted(path for path in items if is_supported_image_file(path))


def _process_single_file(
    service: TaggingService,
    request: DetectionRequest,
    source: Path,
    include_details: bool,
) -> dict:
    image = load_image_file(source)
    result = service.analyze(image, request)
    payload: dict[str, object] = {"tags": result.tags}
    if include_details:
        payload["detections"] = _format_detections(result.detections)
    return payload


def run_source(
    service: TaggingService,
    request: DetectionRequest,
    source: Path,
    include_details: bool,
    recursive: bool,
    pretty: bool,
) -> int:
    if not source.exists():
        print("Erro: caminho informado nao existe.", file=sys.stderr)
        return 1

    if source.is_file():
        payload = _process_single_file(service, request, source, include_details)
        _emit(payload, pretty=pretty)
        return 0

    files = _iter_image_files(source, recursive=recursive)
    if not files:
        print("Erro: diretorio sem imagens suportadas.", file=sys.stderr)
        return 1

    items: list[dict] = []
    for path in files:
        relative_name = str(path.relative_to(source))
        try:
            result = _process_single_file(service, request, path, include_details)
            result["file"] = relative_name
            items.append(result)
        except InputValidationError as exc:
            items.append({"file": relative_name, "tags": [], "error": str(exc)})

    _emit(
        {
            "source": str(source),
            "total": len(items),
            "items": items,
        },
        pretty=pretty,
    )
    return 0


def _draw_detections(frame, detections: list[Detection]) -> None:
    for detection in detections:
        x1, y1, x2, y2 = [int(v) for v in detection.bbox]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (30, 200, 80), 2)
        cv2.putText(
            frame,
            f"{detection.label} {detection.confidence:.2f}",
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (30, 200, 80),
            2,
            cv2.LINE_AA,
        )


def run_webcam(
    service: TaggingService,
    request: DetectionRequest,
    device: int,
    show: bool,
    stride: int,
    print_every: bool,
    include_details: bool,
) -> int:
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        print("Erro: webcam nao disponivel.", file=sys.stderr)
        return 1

    frame_idx = 0
    last_tags: list[str] | None = None
    last_detections: list[Detection] = []

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_idx % max(1, stride) == 0:
                result = service.analyze(frame, request)
                last_detections = result.detections
                if print_every or result.tags != last_tags:
                    payload: dict[str, object] = {"tags": result.tags}
                    if include_details:
                        payload["detections"] = _format_detections(last_detections)
                    _emit(payload, pretty=False)
                    last_tags = result.tags

            if show:
                view = frame.copy()
                _draw_detections(view, last_detections)
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
    try:
        request = DetectionRequest(
            conf_threshold=args.conf,
            max_tags=args.max_tags,
            min_area_ratio=args.min_area,
            include_person=args.include_person,
        )
        service = TaggingService(
            detector=YoloObjectDetector(model_path=args.model),
            label_map=COCO_PT,
        )
    except InputValidationError as exc:
        print(f"Erro de validacao: {exc}", file=sys.stderr)
        return 2

    try:
        if args.source:
            return run_source(
                service=service,
                request=request,
                source=Path(args.source),
                include_details=args.include_details,
                recursive=args.recursive,
                pretty=args.pretty,
            )

        return run_webcam(
            service=service,
            request=request,
            device=args.webcam,
            show=args.show,
            stride=args.stride,
            print_every=args.print_every,
            include_details=args.include_details,
        )
    except InputValidationError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

