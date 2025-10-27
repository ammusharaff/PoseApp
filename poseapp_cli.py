import argparse
from app.main import run_app

def main():
    parser = argparse.ArgumentParser(description="PoseApp CLI")
    parser.add_argument('--backend', choices=['movenet', 'mediapipe'], default='movenet', help='Select pose backend')
    parser.add_argument('--variant', choices=['lightning', 'thunder'], default='lightning', help='Select MoveNet variant')
    parser.add_argument('--add-model', type=str, help='Path to new model to integrate')
    parser.add_argument('--camera', type=int, default=0, help='Camera index to use')
    parser.add_argument('--mode', choices=['freestyle', 'guided'], default='freestyle', help='UI mode')

    args = parser.parse_args()

    # Example: pass args to main window or config
    run_app(backend=args.backend, variant=args.variant, camera=args.camera, mode=args.mode)

    # Example for adding new model (YOLO-Pose etc.)
    if args.add_model:
        print(f"Integrating new model: {args.add_model}")
        # TODO: Logic to move/copy/validate new model file, update config, or run setup

if __name__ == "__main__":
    main()
