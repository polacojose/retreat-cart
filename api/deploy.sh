#!/usr/bin/env bash
	
# Automaticlly generated version number
VERSION="$(git rev-parse --short HEAD)"

build() {

	echo "Building..."

	export jobName=`LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | head -c 10`
	export VERSION=${VERSION} &&

	if test -f Dockerfile; then

		tar -cf - * | gzip -9 | kubectl run ${jobName} --stdin=true --image=gcr.io/kaniko-project/executor:debug -n gocd --restart=Never \
		  -- --dockerfile=Dockerfile --context=tar://stdin --destination=registry.polacoproject.net/retreat-cart-api:${VERSION} --destination=registry.polacoproject.net/retreat-cart-api:latest --cache=true

		termCode=$(kubectl get pod ${jobName} -n gocd -o jsonpath='{.status.containerStatuses[0].state.terminated.exitCode}')
		kubectl delete pod ${jobName} -n gocd

		if [ ${termCode} -ne 0 ]; then
			return ${termCode}
		fi

	fi

  echo "Finished building retreat-cart-api:${VERSION}"
}

update_deployment() {
  
	# Clone deploy repo to temp directory
	DEPLOY_REPO_DIR="/tmp/retreat-cart-deploy"
	rm -rf "$DEPLOY_REPO_DIR"
	git clone git@github.com:polacojose/retreat-cart-deploy.git "$DEPLOY_REPO_DIR"

	echo "Updating deployment retreat-cart to version ${VERSION}"

	cd "$DEPLOY_REPO_DIR/base/"
	kustomize edit set image registry.polacoproject.net/retreat-cart-api:${VERSION}
	cd -

	# Commit and push changes
	git config --global user.email "ci@polacoproject.net"
 	git config --global user.name "CI Bot"
	cd "$DEPLOY_REPO_DIR"
	git add .
	git commit -m "Update image tag to ${VERSION} and configs for build $(date +%Y%m%d-%H%M%S)"
	if ! git push origin main; then
		echo "Push failed, retrying..."
		git pull --rebase origin main
		git push origin main
	fi
	rm -rf "$DEPLOY_REPO_DIR"
	cd -
}

#ENV
export VERSION=$VERSION
export -f build
export -f update_deployment

build &&
update_deployment

