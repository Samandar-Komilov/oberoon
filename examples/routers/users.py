from oberoon import Request, Response, Router


router = Router(
    prefix="/users",
)


@router.get("/{id}/")
async def get_user(request: Request, id: int) -> Response:
    response = Response(200)
    response.set_body(
        f'{{"user_id": {id}, "type": "{type(id).__name__}"}}'.encode(),
        content_type="application/json",
    )
    return response
